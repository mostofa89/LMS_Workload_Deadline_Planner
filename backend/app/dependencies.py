from __future__ import annotations

import uuid
from typing import Generator
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import NotAuthenticated
from app.schemas import Principal


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


def get_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise NotAuthenticated("Missing bearer token")
    token = auth_header.removeprefix("Bearer ").strip()
    from app.security import decode_jwt_token
    claims = decode_jwt_token(token, purpose="access")
    if not claims or "sub" not in claims:
        raise NotAuthenticated("Invalid or expired access token")
    return Principal(
        id=uuid.UUID(claims["sub"]),
        email=claims.get("email", ""),
        roles=claims.get("roles", []),
        capabilities=set(claims.get("capabilities", [])),
        institution_id=uuid.UUID(claims["inst"]) if claims.get("inst") else None,
    )


get_principle = get_principal
