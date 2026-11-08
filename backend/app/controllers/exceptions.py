from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"error": self.message, "code": self.code}
        if self.details is not None:
            data["details"] = self.details
        return data


class ValidationFailed(AppError):
    def __init__(
        self,
        message: str = "Validation failed.",
        code: str = "VALIDATION_FAILED",
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code, details=details)


class PermissionDenied(AppError):
    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        code: str = "PERMISSION_DENIED",
        status_code: int = 403,
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code, details=details)


class NotAuthenticated(AppError):
    def __init__(
        self,
        message: str = "Authentication required.",
        code: str = "NOT_AUTHENTICATED",
        status_code: int = 401,
        details: Any = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code, details=details)
