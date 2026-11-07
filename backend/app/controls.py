from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import AppError, PermissionDenied, ValidationFailed
from app.formatting import (
    SIGNUP_KEY_ROLES,
    _human_code,
    _link_from_invite,
    _role_prefix,
    _signup_rejected,
    check_throttle,
    ensure_no_escalation,
    get_role,
    normalize_code_text,
    normalize_email,
)
from app.models import (
    GuardianInvite,
    GuardianLink,
    RefreshToken,
    RegistrationKey,
    Role,
    User,
    UserRole,
)
from app.schemas import LoginResult, Principal, TokenPair
from app.security import (
    create_jwt_token,
    hash_password,
    issue_email_verification,
    password_problems,
    preferences,
    record,
    register_failure,
    send_transactional_email,
    token_digest,
    utcnow,
    verify_password,
)

# ====================================================================
# Sign Up Controls                                                 ||
# ====================================================================


def _is_expired(expires_at: datetime | None, now: datetime) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None and now.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    elif expires_at.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return expires_at <= now


def issue_registration_key(
    db: Session,
    *,
    institution_id: uuid.UUID,
    role_key: str,
    scope_type: str,
    scope_id: uuid.UUID | None,
    label: str,
    max_uses: int,
    expires_in_days: int,
    actor_id: uuid.UUID | None,
    ip: str | None = None,
    actor: Principal | None = None,
) -> tuple[RegistrationKey, str]:

    if role_key not in SIGNUP_KEY_ROLES:
        raise ValidationFailed("That role cannot be used for self-signup.", code="ROLE_NOT_ALLOWED")

    role = get_role(db, institution_id, role_key)
    if actor is not None:
        ensure_no_escalation(actor, {c.capability for c in getattr(role, "capabilities", [])})

    if scope_type not in ("institution", "department", "program", "section"):
        raise ValidationFailed("Choose a valid Scope", code="INVALID_SCOPE")

    if scope_type != "institution" and scope_id is None:
        raise ValidationFailed(
            "Choose the department, program or section this key applies to.",
            code="SCOPE_ID_REQUIRED",
        )

    if scope_type == "institution":
        scope_id = None

    if not (1 <= max_uses <= 500 and 1 <= expires_in_days <= 90):
        raise ValidationFailed(
            "Max uses must be between 1 and 500 and expires in days must be between 1 and 90.",
            code="INVALID_MAX_USES_OR_EXPIRES",
        )

    raw = _role_prefix(role_key) + "-" + _human_code(6)
    norm = normalize_code_text(raw)
    k = RegistrationKey(
        institution_id=institution_id,
        role_key=role_key,
        scope_type=scope_type,
        scope_id=scope_id,
        label=label.strip()[:200],
        key_hash=token_digest("regkey:" + norm),
        key_hint=raw[-4:],
        max_uses=max_uses,
        expires_at=utcnow() + timedelta(days=expires_in_days),
        created_by=actor_id,
    )
    db.add(k)
    db.flush()
    record(
        db,
        "registration_key_issued",
        actor_id=actor_id,
        institution_id=institution_id,
        target_type="registration_key",
        target_id=k.id,
        summary=f"Issued registration key {k.key_hint} for role {role_key} with scope {scope_type} and label '{label}'",
        meta={"role": role.key, "scope_type": scope_type, "max_uses": max_uses, "days": expires_in_days},
    )
    return k, raw


def signup(
    db: Session,
    *,
    account_type: str,
    full_name: str,
    email: str,
    password: str,
    institution_id: uuid.UUID | None = None,
    registration_key: str | None = None,
    role_key: str | None = None,
    guardian_code: str | None = None,
    ip: str | None = None,
    timezone: str = "UTC",
) -> User:
    now = utcnow()
    email = normalize_email(email)
    full_name = " ".join(full_name.split())
    problems = password_problems(password, email)
    if problems:
        raise ValidationFailed("Password is not strong enough: " + "; ".join(problems), code="WEAK_PASSWORD")

    guess_keys = [("signupcode:" + (ip or "unknown"), 50)]
    check_throttle(db, guess_keys, now)

    # Check if user already exists
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        send_transactional_email(
            db,
            existing,
            "signup_existing_account",
            {"app": "LMS Workload & Deadline Planner", "link": get_settings().public_app_url + "/login"},
            key=f"signup-existing:{existing.id}:{now:%Y%m%d%H}",
        )
        raise ValidationFailed("An account with this email already exists.", code="USER_ALREADY_EXISTS")

    key_row: RegistrationKey | None = None
    invite: GuardianInvite | None = None
    inst_id: uuid.UUID | None = institution_id

    if account_type in ("student", "staff"):
        if not registration_key:
            raise ValidationFailed("Enter a valid registration code to sign up.", code="REGISTRATION_KEY_REQUIRED")

        key_row = db.scalar(
            select(RegistrationKey)
            .where(RegistrationKey.key_hash == token_digest("regkey:" + normalize_code_text(registration_key)))
            .with_for_update()
        )
        if (
            key_row is None
            or key_row.revoked_at is not None
            or _is_expired(key_row.expires_at, now)
            or key_row.uses >= key_row.max_uses
        ):
            register_failure(db, guess_keys, now)
            raise _signup_rejected()

        expected_role = role_key or ("student" if account_type == "student" else None)
        if expected_role is None or key_row.role_key != expected_role:
            raise ValidationFailed("That signup key is for a different role.", code="ROLE_KEY_MISMATCH")

        inst_id = key_row.institution_id
        if account_type == "student":
            if inst_id is None:
                raise ValidationFailed("That Signup key is not valid for student accounts.", code="INVALID_STUDENT_KEY")

            if institution_id is not None and institution_id != inst_id:
                raise PermissionDenied("Institution mismatch for registration key.", code="INSTITUTION_MISMATCH")

            if not get_settings(db, inst_id, "signup.student_open"):
                raise PermissionDenied("Student signup is not open for that institution.", code="STUDENT_SIGNUP_CLOSED")

            domains = [d.lower().strip() for d in (get_settings(db, inst_id, "signup.student_email_domains") or [])]
            if domains and not any(email.endswith("@" + d) for d in domains):
                raise ValidationFailed(
                    "Use your institution email address (" + ", ".join("@" + d for d in domains) + ").",
                    code="EMAIL_DOMAIN_NOT_ALLOWED",
                )

        key_row.uses += 1

    elif account_type == "parent":
        if not guardian_code:
            raise ValidationFailed("Enter a valid guardian code to sign up.", code="GUARDIAN_CODE_REQUIRED")

        norm_code = normalize_code_text(guardian_code)
        invite = db.scalar(
            select(GuardianInvite)
            .where(
                (GuardianInvite.code_hash == token_digest("guardian:" + norm_code))
                | (GuardianInvite.code_hash == token_digest("guardian : " + norm_code))
            )
            .with_for_update()
        )
        student = db.get(User, invite.student_id) if invite else None
        if (
            invite is None
            or student is None
            or invite.used_at is not None
            or invite.revoked_at is not None
            or _is_expired(invite.expires_at, now)
        ):
            raise _signup_rejected()

        inst_id = student.institution_id
        if not get_settings(db, inst_id, "signup.parent_open"):
            raise PermissionDenied("Parent signup is not open for that institution.", code="PARENT_SIGNUP_CLOSED")

    else:
        raise ValidationFailed("Choose a valid account type.", code="INVALID_ACCOUNT_TYPE")

    user = User(
        institution_id=inst_id,
        email=email,
        full_name=full_name,
        timezone=timezone or "UTC",
    )
    user.password_hash = hash_password(password)
    user.password_changed_at = now
    db.add(user)
    db.flush()

    preferences(db, user.id)
    if invite is not None:
        _link_from_invite(db, user, invite, now)

    record(
        db,
        "access.self_signup",
        category="access",
        actor_id=user.id,
        institution_id=inst_id,
        target_type="user",
        target_id=user.id,
        ip=ip,
        summary=f"Self-signup for {account_type} account",
        meta={
            "account_type": account_type,
            "role_key": role_key,
            "institution_id": str(inst_id) if inst_id else None,
            "guardian_code": guardian_code,
            "registration_key": registration_key,
        },
    )
    issue_email_verification(db, user)
    db.commit()
    return user


# ====================================================================
# Authentication Controls                                          ||
# ====================================================================


def login(
    db: Session,
    email: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> LoginResult:
    email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        from app.errors import invalid_credentials
        raise invalid_credentials()

    if user.status != "active":
        raise PermissionDenied("Your account is not active.", code="ACCOUNT_INACTIVE")

    s = get_settings()
    now = utcnow()
    user.last_login_at = now
    user.last_active_at = now

    access_token = create_jwt_token(
        subject=user.id,
        purpose="access",
        ttl=timedelta(minutes=s.access_token_minutes),
        extra={
            "email": user.email,
            "inst": str(user.institution_id) if user.institution_id else None,
        },
    )
    raw_refresh = secrets.token_urlsafe(48)
    refresh_hash = token_digest("refresh:" + raw_refresh)
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=now + timedelta(days=s.refresh_token_days),
    )
    db.add(db_refresh)
    db.commit()

    tokens = TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=s.access_token_minutes * 60,
    )
    return LoginResult(tokens=tokens)


def get_session_by_token(db: Session, raw_token: str) -> RefreshToken | None:
    now = utcnow()
    refresh_hash = token_digest("refresh:" + raw_token)
    sess = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == refresh_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    if sess and not _is_expired(sess.expires_at, now):
        return sess
    return None


def revoke_session(db: Session, session_or_token: RefreshToken | str, reason: str = "logout") -> None:
    now = utcnow()
    if isinstance(session_or_token, RefreshToken):
        session_or_token.revoked_at = now
    else:
        refresh_hash = token_digest("refresh:" + session_or_token)
        sess = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == refresh_hash))
        if sess:
            sess.revoked_at = now


def refresh_session(db: Session, raw_refresh_token: str) -> TokenPair:
    sess = get_session_by_token(db, raw_refresh_token)
    if not sess:
        from app.exceptions import NotAuthenticated
        raise NotAuthenticated("Invalid or expired session. Please log in again.")

    user = db.get(User, sess.user_id)
    if not user or user.status != "active":
        from app.exceptions import PermissionDenied
        raise PermissionDenied("User account is inactive.")

    s = get_settings()
    now = utcnow()
    user.last_active_at = now

    access_token = create_jwt_token(
        subject=user.id,
        purpose="access",
        ttl=timedelta(minutes=s.access_token_minutes),
        extra={
            "email": user.email,
            "inst": str(user.institution_id) if user.institution_id else None,
        },
    )

    # Revoke old session and issue rotated refresh token
    sess.revoked_at = now
    new_raw_refresh = secrets.token_urlsafe(48)
    new_refresh_hash = token_digest("refresh:" + new_raw_refresh)
    new_db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=new_refresh_hash,
        expires_at=now + timedelta(days=s.refresh_token_days),
        replaced_by_id=sess.id,
    )
    db.add(new_db_refresh)
    db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=new_raw_refresh,
        expires_in=s.access_token_minutes * 60,
    )
