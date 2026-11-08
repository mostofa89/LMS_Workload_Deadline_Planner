from __future__ import annotations

import hmac
import secrets
from typing import Any
from fastapi import Request, Response

from app.config import get_settings
from app.controllers.exceptions import AppError, NotAuthenticated
from app.views.schemas import RefreshIn, TokenPair

REFRESH_COOKIE = "lms_refresh"
CSRF_COOKIE = "lms_csrf"
CSRF_HEADER = "x-csrf-token"


def set_session_cookie(resp: Response, token_or_pair: str | TokenPair) -> None:
    s = get_settings()
    refresh_token = token_or_pair.refresh_token if isinstance(token_or_pair, TokenPair) else str(token_or_pair)
    resp.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=s.refresh_token_days * 86400,
        httponly=True,
        secure=s.cookie_secure,
        samesite="lax",
        path="/",
        domain=s.cookie_domain,
    )

    resp.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(24),
        max_age=s.refresh_token_days * 86400,
        httponly=False,
        secure=s.cookie_secure,
        samesite="lax",
        path="/",
        domain=s.cookie_domain,
    )


# Alias with underscore for compatibility
_set_session_cookie = set_session_cookie


def clear_cookies(resp: Response) -> None:
    s = get_settings()
    resp.delete_cookie(REFRESH_COOKIE, path="/", domain=s.cookie_domain)
    resp.delete_cookie(CSRF_COOKIE, path="/", domain=s.cookie_domain)


_clear_cookies = clear_cookies


def refresh_from_request(request: Request, body: RefreshIn | None = None) -> str:
    if body and body.refresh_token:
        return body.refresh_token

    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise NotAuthenticated("No refresh token provided in cookies or payload.")

    cookie_csrf = request.cookies.get(CSRF_COOKIE, "")
    header_csrf = request.headers.get(CSRF_HEADER, "")
    if cookie_csrf and header_csrf:
        if not hmac.compare_digest(cookie_csrf, header_csrf):
            raise AppError("Your session CSRF check failed. Reload the page and try again.", code="CSRF_FAILED", status_code=403)

    return raw


_refresh_from_request = refresh_from_request
