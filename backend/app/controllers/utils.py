from __future__ import annotations

from datetime import datetime, timezone

from app.controllers.exceptions import AppError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
