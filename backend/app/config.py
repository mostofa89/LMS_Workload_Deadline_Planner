from __future__ import annotations

import base64
import os
import secrets
from functools import lru_cache
from typing import Any
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _generate_default_fernet_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lms_workload_planner"
    password_min_length: int = 8
    jwt_secret: SecretStr = SecretStr("insecure-dev-secret-key-for-jwt-signing-minimum-32-bytes!!")
    jwt_audience: str = "lms-workload-planner"
    jwt_issuer: str = "lms-api"
    encryption_key: SecretStr = SecretStr(_generate_default_fernet_key())
    token_pepper: SecretStr = SecretStr("token-pepper-default-secret-string")
    public_app_url: str = "http://localhost:3000"
    refresh_token_days: int = 7
    access_token_minutes: int = 15
    cookie_secure: bool = False
    cookie_domain: str | None = None

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Ensure postgresql:// and postgres:// URLs use the psycopg3 driver."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        return v


@lru_cache
def _get_app_settings() -> Settings:
    return Settings()


def get_settings(*args: Any, **kwargs: Any) -> Any:
    """Retrieve global application settings or an institution-scoped setting."""
    if not args and not kwargs:
        return _get_app_settings()

    if len(args) >= 3:
        _db, _inst_id, key = args[0], args[1], args[2]
        default = args[3] if len(args) > 3 else kwargs.get("default", None)
        defaults = {
            "signup.student_open": True,
            "signup.parent_open": True,
            "signup.student_email_domains": [],
        }
        return defaults.get(key, default)

    return _get_app_settings()


settings: Settings = _get_app_settings()
