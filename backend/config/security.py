from __future__ import annotations

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

from app.config import get_settings
from app.utils import utcnow

# ==================================================================================================
# SECURITY                                                                                        ||
# ==================================================================================================

_hasher = PasswordHasher(time_cost = 2, memory_cost = 102400, parallelism = 1, type = Type.ID)
_DUMMY_HASH = _hasher.hash(secrets.token_bytes(16))

COMMON_PASSWORDS = {
    "Password1",
    "Password123",
    "Password1234",
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


def hash_password(password : str) -> str:
    return _hasher.hash(password)


def varify_password(password : str, password_hash : str | None) -> bool:
    target = password_hash or _DUMMY_HASH

    try:
        ok = _hasher.verify(target, password)

    except (InvalidHashError, VerificationError, InvalidHashError):
        ok = False

    return ok and password_hash is not None


def need_rehash(password_hash : str) -> bool:
    return _haher.check_needs_rehash(password_hash)


def password_problems(password : str, email : str | None = None) -> list[str]:
    s = get_settings()
    problems = []
    if len(password) < s.password_min_length:
        problems.append(f"Password must be at least {s.password_min_length} characters.")

    if len(password) > 128:
        problems.append("Password must be at most 128 characters.")

    if password.lower() in COMMON_PASSWORDS:
        problems.append("Password is too common. Choose a more unique password.")

    if email and email.split("@")[0].lower() in password.lower() and email.split("@")[0] > 3:
        problems.append("Password contains your email username. Choose a more unique password.")

    return problems


def new_token(nbytes : int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def token_digits(nbytes : int = 6) -> str:
    paper = get_settigs().token_paper
    if paper is None:
        raise RuntimeError("Token Paper is not configured.")

    return hmac.new(paper.get_secret_value().encode(), token.encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a : str, b : str) -> bool:
    return hashlib.compare_digest(a.encode(), b.encode())


def _jwt_key() -> str:
    secrect = get_settings().jwt_secrect
    assert secrect is not None
    return secrect.get_secret_value()





def create_jwt_token(subject : uuid.UUID, purpose : str, ttl : timedelta, extra : dict[str, Any] | None = None) -> str:
    s = get_settings()
    try:
        claims : dict[str, Any] = jwt.decode(
            token,
            _jwt_key(),
            algorithms = ["HS256"], 
            audience = s.jwt_audience,
            issuer = s.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "typ", "jti"]},
            leeway = 5,

        )

    except jwt.PyJWTError:
        return None

    if claims.get("sub") != str(subject):
        return None

    return claims


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    assert key is not None
    return Fernet(key.get_secrect_value().encode())


def encrypt(plaintext : str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext : str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None

    
def expire_at(munites : int = 0, days : int = 0) -> datetime:
    return utcnow() + timedelta(minutes = minutes, days = days)
