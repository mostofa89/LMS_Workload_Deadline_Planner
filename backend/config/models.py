from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Role labels for display
ROLE_LABELS = {
    "student": "Student",
    "instructor": "Instructor",
    "admin": "System Administrator",
    "superadmin": "Super Administrator",
    "teaching_assistant": "Teaching Assistant",
    "department_head": "Department Head",
    "parent": "Parent / Guardian",
    "advisor": "Academic Advisor",
    "registrar": "Registrar",
    "support": "Support / Help Desk",
    "coordinator": "Course Coordinator",
}


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False)
    email = Column(String(190), nullable=False, unique=True, index=True)
    password_hash = Column(String(400), nullable=False)
    role = Column(String(80), nullable=False, index=True)
    department = Column(String(120), nullable=False, default="", index=True)
    avatarInitials = Column(String(8), nullable=False, default="")
    status = Column(String(50), nullable=False, default="active", index=True)
    lastActive = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "roleName": ROLE_LABELS.get(self.role, self.role),
            "department": self.department,
            "avatarInitials": self.avatarInitials,
            "status": self.status,
            "lastActive": self.lastActive.isoformat() if self.lastActive else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    capabilities = Column(JSONB, nullable=False, default=list)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = Column(
        String(64),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    scope_type = Column(String(20), primary_key=True, default="global")
    scope_id = Column(String(64), primary_key=True, default="")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(64),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by_id = Column(
        String(64),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class PermissionOverride(Base):
    __tablename__ = "permission_overrides"

    # Must match the role string used by permissions.py.
    role = Column(String(80), primary_key=True)
    overrides = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class Record(Base):
    __tablename__ = "records"

    collection = Column(String(80), primary_key=True)
    id = Column(String(64), primary_key=True)
    seq = Column(Integer, nullable=False, default=0)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )