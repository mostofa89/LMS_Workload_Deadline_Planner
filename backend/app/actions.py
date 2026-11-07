from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import RefreshToken


def revoke_all_user_sessions(db: Session, user_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()
