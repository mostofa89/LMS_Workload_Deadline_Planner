from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Principal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    roles: list[str] = Field(default_factory=list)
    capabilities: set[str] = Field(default_factory=set)
    institution_id: uuid.UUID | None = None
    scope_type: str = "institution"
    scope_id: uuid.UUID | None = None


Principle = Principal


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int = 900
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class LoginOut(BaseModel):
    status: str
    access_token: str | None = None
    expires_in: int | None = None
    mfa_token: str | None = None
    methods: list[str] | None = None


class RefreshIn(BaseModel):
    refresh_token: str | None = None


RefreshIN = RefreshIn


class LoginResult(BaseModel):
    tokens: TokenPair | None = None
    enrollment_required: bool = False
    mfa_required: bool = False
    mfa_token: str | None = None
    mfa_methods: list[str] | None = None


class SignupIn(BaseModel):
    account_type: str = "student"
    full_name: str
    email: EmailStr
    password: str
    institution_id: uuid.UUID | None = None
    registration_key: str | None = None
    role_key: str | None = None
    guardian_code: str | None = None
    timezone: str = "UTC"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    status: str
    institution_id: uuid.UUID | None = None
    timezone: str = "UTC"


class AuthNamespace:
    LoginIn = LoginIn
    LoginOut = LoginOut
    RefreshIn = RefreshIn
    RefreshIN = RefreshIN
    Principal = Principal
    Principle = Principle
    TokenPair = TokenPair
    LoginResult = LoginResult
    SignupIn = SignupIn
    UserOut = UserOut


auth = AuthNamespace()
