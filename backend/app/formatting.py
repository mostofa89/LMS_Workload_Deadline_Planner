from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import AppError, PermissionDenied, ValidationFailed
from app.models import GuardianInvite, GuardianLink, Role, User

STAF_SIGNUP_ROLE = (
    "instructor",
    "teaching_assistant",
    "advisor",
    "admin",
    "superadmin",
    "coordinator",
    "registrar",
    "register",
    "department_head",
    "support",
)
STAFF_SIGNUP_ROLE = STAF_SIGNUP_ROLE

today = datetime.now()
SIGNUP_KEY_ROLES = ("student", *STAF_SIGNUP_ROLE)
KEY_ALPHABET = "LMS-F26-9XK72"

ROLE_KEY_PREFIX: dict[str, str] = {
    "student": "STU",
    "instructor": "INST",
    "teaching_assistant": "TA",
    "coordinator": "CORD",
    "department_head": "DHOD",
    "advisor": "ADV",
    "registrar": "REG",
    "register": "REG",
    "admin": "ADM",
    "superadmin": "SADM",
    "support": "SUP",
}


def _human_code(groups: int, size: int = 4) -> str:
    return "-".join("".join(secrets.choice(KEY_ALPHABET) for _ in range(size)) for _ in range(groups))


def _role_prefix(role_key: str) -> str:
    return ROLE_KEY_PREFIX.get(role_key, "KEY")


def normalize_code_text(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def normalize_code(code: str) -> str:
    return normalize_code_text(code)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def check_throttle(db: Session, keys: list[tuple[str, int]], now: datetime) -> None:
    pass


def ensure_no_escalation(actor: Any, capabilities: set[str]) -> None:
    if actor is None:
        return
    actor_caps = set(getattr(actor, "capabilities", set()))
    if "admin" in actor_caps or "superadmin" in getattr(actor, "roles", []):
        return
    missing = capabilities - actor_caps
    if missing:
        raise PermissionDenied("Cannot grant capabilities you do not possess.", code="PRIVILEGE_ESCALATION")


def get_role(db: Session, institution_id: uuid.UUID | None, role_key: str) -> Role:
    stmt = select(Role).where(Role.key == role_key)
    if institution_id:
        stmt = stmt.where((Role.institution_id == institution_id) | (Role.institution_id.is_(None)))
    role = db.scalar(stmt)
    if not role:
        role = Role(
            key=role_key,
            name=role_key.replace("_", " ").title(),
            is_system=True,
            institution_id=institution_id,
        )
        db.add(role)
        db.flush()
    return role


def _link_from_invite(db: Session, user: User, invite: GuardianInvite, now: datetime) -> GuardianLink:
    link = GuardianLink(
        guardian_id=user.id,
        student_id=invite.student_id,
        status="active",
        student_consented_at=now,
        verified_at=now,
        permitted_fields=invite.permitted_fields,
        notify=invite.notify,
        invite_id=invite.id,
    )
    invite.used_at = now
    invite.used_by = user.id
    db.add(link)
    db.flush()
    return link


def _signup_rejected() -> AppError:
    return AppError(
        "The registration code is invalid, expired, or has reached its usage limit.",
        code="SIGNUP_REJECTED",
        status_code=400,
    )
