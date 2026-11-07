from __future__ import annotations

from app.exceptions import AppError


def invalid_credentials() -> AppError:
    return AppError(
        "Email or Password is Incorrect. Please check your credentials and try again.",
        code="INVALID_CREDENTIALS",
        status_code=401,
    )


def invalid_code() -> AppError:
    return AppError(
        "The code is invalid. Check that you have entered it correctly, and that it has not expired or been used up.",
        code="INVALID_CODE",
        status_code=400,
    )


def _verify_code_rejected() -> AppError:
    return AppError(
        "The code is invalid. Check that you have entered it correctly, and that it has not expired or been used up.",
        code="VERIFY_CODE_REJECTED",
        status_code=400,
    )


def _signup_rejected() -> AppError:
    return AppError(
        "The registration code is invalid, expired, or has reached its usage limit.",
        code="SIGNUP_REJECTED",
        status_code=400,
    )
