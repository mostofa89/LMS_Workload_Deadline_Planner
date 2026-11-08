from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Record, User, UserPreferences
from app.controllers.utils import utcnow

# ==================================================================================================
# SECURITY                                                                                        ||
# ==================================================================================================

_hasher = PasswordHasher(time_cost=2, memory_cost=102400, parallelism=1, type=Type.ID)
_DUMMY_HASH = _hasher.hash(secrets.token_bytes(16))

COMMON_PASSWORDS = {
    "password1",
    "password123",
    "password1234",
    "123456789012",
    "qwertyuiopas",
    "letmein12345",
    "iloveyou1234",
    "welcome12345",
    "password123!",
    "adminadmin12",
    "changeme1234",
    "universityof",
}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    target = password_hash or _DUMMY_HASH
    try:
        ok = _hasher.verify(target, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        ok = False
    return bool(ok and password_hash is not None)


varify_password = verify_password


def need_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


needs_rehash = need_rehash


def password_problems(password: str, email: str | None = None) -> list[str]:
    s = get_settings()
    problems: list[str] = []
    if len(password) < s.password_min_length:
        problems.append(f"Password must be at least {s.password_min_length} characters.")

    if len(password) > 128:
        problems.append("Password must be at most 128 characters.")

    if password.lower() in COMMON_PASSWORDS:
        problems.append("Password is too common. Choose a more unique password.")

    if email:
        username = email.split("@")[0].lower()
        if len(username) > 3 and username in password.lower():
            problems.append("Password contains your email username. Choose a more unique password.")

    return problems


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def token_digits(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def token_digest(token: str) -> str:
    pepper = get_settings().token_pepper
    pepper_bytes = pepper.get_secret_value().encode() if hasattr(pepper, "get_secret_value") else str(pepper).encode()
    return hmac.new(pepper_bytes, token.encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def _jwt_key() -> str:
    secret = get_settings().jwt_secret
    if hasattr(secret, "get_secret_value"):
        return secret.get_secret_value()
    return str(secret)


def create_jwt_token(
    subject: uuid.UUID | str,
    purpose: str,
    ttl: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    s = get_settings()
    now = utcnow()
    claims: dict[str, Any] = {
        "sub": str(subject),
        "typ": purpose,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": secrets.token_hex(16),
        "iss": s.jwt_issuer,
        "aud": s.jwt_audience,
    }
    if extra:
        claims.update(extra)
    return jwt.encode(claims, _jwt_key(), algorithm="HS256")


def decode_jwt_token(
    token: str,
    purpose: str | None = None,
) -> dict[str, Any] | None:
    s = get_settings()
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            _jwt_key(),
            algorithms=["HS256"],
            audience=s.jwt_audience,
            issuer=s.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "typ", "jti"]},
            leeway=5,
        )
    except jwt.PyJWTError:
        return None

    if purpose and claims.get("typ") != purpose:
        return None

    return claims


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    assert key is not None
    val = key.get_secret_value() if hasattr(key, "get_secret_value") else str(key)
    try:
        return Fernet(val.encode())
    except Exception:
        key_bytes = base64.urlsafe_b64encode(hashlib.sha256(val.encode()).digest())
        return Fernet(key_bytes)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str | None:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None


def expire_at(minutes: int = 0, days: int = 0) -> datetime:
    return utcnow() + timedelta(minutes=minutes, days=days)


# ==================================================================================================
# AUDIT & AUTH HELPERS                                                                            ||
# ==================================================================================================

def record(
    db: Session,
    action: str,
    *,
    category: str = "general",
    actor_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    summary: str = "",
    ip: str | None = None,
    meta: dict[str, Any] | None = None,
) -> Record:
    rec = Record(
        category=category,
        action=action,
        actor_id=actor_id,
        institution_id=institution_id,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        ip=ip,
        meta=meta or {},
    )
    db.add(rec)
    return rec


def preferences(db: Session, user_id: uuid.UUID) -> UserPreferences:
    existing = db.get(UserPreferences, user_id)
    if existing:
        return existing
    pref = UserPreferences(user_id=user_id)
    db.add(pref)
    return pref


def send_transactional_email(
    db: Session,
    user: User,
    template: str,
    context: dict[str, Any],
    key: str | None = None,
) -> None:
    record(
        db,
        "email.sent",
        category="notification",
        target_type="user",
        target_id=user.id,
        summary=f"Sent {template} email to {user.email}",
        meta={"template": template, "key": key},
    )


def issue_email_verification(db: Session, user: User) -> None:
    token = new_token(32)
    send_transactional_email(
        db,
        user,
        "email_verification",
        {"verification_token": token, "email": user.email},
        key=f"verify:{user.id}",
    )


issues_email_varification = issue_email_verification


def register_failure(db: Session, guess_keys: list[tuple[str, int]], now: datetime) -> None:
    pass


def normalize_code_text(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def normalize_email(email: str) -> str:
    return email.strip().lower()
