from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, Timestamps, UUIDPk, utcnow


class Institution(UUIDPk, Timestamps, Base):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Record(UUIDPk, Timestamps, Base):
    __tablename__ = "records"

    category: Mapped[str] = mapped_column(String(60), default="general", index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    summary: Mapped[str] = mapped_column(String(500), default="")
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

#================================================================================
# User and Role Management Models                                              ||
#================================================================================
class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    locale: Mapped[str] = mapped_column(String(16), default="en")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    department: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    avatar_initials: Mapped[str] = mapped_column(String(8), default="", server_default="")
    title: Mapped[str] = mapped_column(String(200), default="", server_default="")
    external_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def name(self) -> str:
        return self.full_name

    institution: Mapped[Institution | None] = relationship(lazy="joined")
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="UserRole.user_id"
    )
    preferences: Mapped[UserPreferences | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Role(UUIDPk, Timestamps, Base):
    __tablename__ = "roles"

    __table_args__ = (UniqueConstraint("institution_id", "key"),)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True
    )
    key: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    default_scope: Mapped[str] = mapped_column(String(20), default="institution")

    capabilities: Mapped[list[RoleCapability]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class PermissionOverride(Timestamps, Base):
    __tablename__ = "permission_overrides"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), primary_key=True
    )
    role_key: Mapped[str] = mapped_column(String(60), primary_key=True)
    overrides: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class RoleCapability(Base):
    __tablename__ = "role_capabilities"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    capability: Mapped[str] = mapped_column(String(60), primary_key=True)


class UserRole(UUIDPk, Timestamps, Base):
    __tablename__ = "user_roles"

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id"),
        Index("ix_user_roles_scope", "scope_type", "scope_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    scope_type: Mapped[str] = mapped_column(String(20), default="institution")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    granted_capabilities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    user: Mapped[User] = relationship(back_populates="roles", foreign_keys=[user_id])
    role: Mapped[Role] = relationship(lazy="joined")


class UserPreferences(Timestamps, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    channels: Mapped[dict[str, bool]] = mapped_column(
        JSON, default=lambda: {"in_app": True, "email": True, "sms": False, "push": False}
    )

    events: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    digest: Mapped[str] = mapped_column(String(10), default="none")
    available_hours_per_week: Mapped[float] = mapped_column(Float, default=20.0)
    daily_available_hours: Mapped[float] = mapped_column(Float, default=4.0)
    study_block_minutes: Mapped[int] = mapped_column(Integer, default=60)
    study_days: Mapped[list[int]] = mapped_column(JSON, default=lambda: [0, 1, 2, 3, 4, 5, 6])
    study_window_start: Mapped[str] = mapped_column(String(5), default="08:00")
    study_window_end: Mapped[str] = mapped_column(String(5), default="22:00")
    advisor_visibility: Mapped[str] = mapped_column(String(10), default="aggregate")
    leaderboard_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="preferences")


class AdvisorAssignment(UUIDPk, Timestamps, Base):
    __tablename__ = "advisor_assignments"
    __table_args__ = (UniqueConstraint("advisor_id", "student_id"),)
    advisor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class GuardianLink(UUIDPk, Timestamps, Base):
    __tablename__ = "guardian_links"

    __table_args__ = (UniqueConstraint("guardian_id", "student_id"),)
    guardian_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    student_consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    permitted_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    notify: Mapped[bool] = mapped_column(Boolean, default=False)
    invite_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("guardian_invites.id", ondelete="SET NULL"), nullable=True)


class GuardianInvite(UUIDPk, Timestamps, Base):
    __tablename__ = "guardian_invites"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    code_hint: Mapped[str] = mapped_column(String(8))
    guardian_email: Mapped[str] = mapped_column(String(320), default="", server_default="")
    relation: Mapped[str] = mapped_column(String(40), default="", server_default="")
    permitted_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    notify: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RegistrationKey(UUIDPk, Timestamps, Base):
    __tablename__ = "registration_keys"

    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), index=True)
    role_key: Mapped[str] = mapped_column(String(60))
    scope_type: Mapped[str] = mapped_column(String(20), default="institution")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    label: Mapped[str] = mapped_column(String(200), default="")
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    key_hint: Mapped[str] = mapped_column(String(8))
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(UUIDPk, Timestamps, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True)
