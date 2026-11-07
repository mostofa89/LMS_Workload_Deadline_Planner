from __future__ import annotations

from datetime import datetime, timezone

from app.exceptions import AppError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
