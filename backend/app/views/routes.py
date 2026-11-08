from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.views.cookies import clear_cookies, refresh_from_request, set_session_cookie
from app.views.dependencies import client_ip, get_db, get_principal, get_principle
from app.controllers.exceptions import NotAuthenticated
from app.models import User
from app.views.schemas import Principal, Principle, auth as schemas
from app.controllers import controls

identity_router = APIRouter(prefix="/auth", tags=["auth"])
# Alias for typo compatibility
identify_router = identity_router

# =======================================================================
# Authentication Views                                                ||
# =======================================================================


@identity_router.post("/signup", response_model=schemas.UserOut, status_code=201)
def signup_view(
    body: schemas.SignupIn,
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    return controls.signup(
        db,
        account_type=body.account_type,
        full_name=body.full_name,
        email=body.email,
        password=body.password,
        institution_id=body.institution_id,
        registration_key=body.registration_key,
        role_key=body.role_key,
        guardian_code=body.guardian_code,
        ip=client_ip(request),
        timezone=body.timezone,
    )


@identity_router.post("/login", response_model=schemas.LoginOut)
def login(
    body: schemas.LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> schemas.LoginOut:
    out = controls.login(db, body.email, body.password, client_ip(request), request.headers.get("user-agent"))
    if out.tokens:
        set_session_cookie(response, out.tokens)
        return schemas.LoginOut(
            status="authenticated",
            access_token=out.tokens.access_token,
            expires_in=out.tokens.expires_in,
        )

    if out.enrollment_required:
        return schemas.LoginOut(status="mfa_enrollment_required", mfa_token=out.mfa_token)

    return schemas.LoginOut(status="mfa_required", mfa_token=out.mfa_token, methods=out.mfa_methods)


@identity_router.post("/refresh", response_model=schemas.LoginOut)
def refresh_session_view(
    request: Request,
    response: Response,
    body: schemas.RefreshIn | None = None,
    db: Session = Depends(get_db),
) -> schemas.LoginOut:
    raw = refresh_from_request(request, body)
    pair = controls.refresh_session(db, raw)
    set_session_cookie(response, pair)
    return schemas.LoginOut(
        status="authenticated",
        access_token=pair.access_token,
        expires_in=pair.expires_in,
    )


@identity_router.get("/me", response_model=schemas.UserOut)
def get_current_user_profile(
    principal: schemas.Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, principal.id)
    if not user:
        raise NotAuthenticated("User not found.")
    return user


@identity_router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    body: schemas.RefreshIn | None = None,
    db: Session = Depends(get_db),
) -> Response:
    try:
        raw = refresh_from_request(request, body)
        sess = controls.get_session_by_token(db, raw)
        if sess:
            controls.revoke_session(db, sess, "logout")
            db.commit()
    except NotAuthenticated:
        pass

    resp = Response(status_code=204)
    clear_cookies(resp)
    return resp
