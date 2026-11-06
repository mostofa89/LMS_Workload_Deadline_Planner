from __future__ import annotations

from app.database import Base, Timestamps, UUIDPk

# ==================================================================================================
# USERS                                                                                           ||
# ==================================================================================================

class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True) 
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(255))  
    status: Mapped[str] = mapped_column(String(20), default="active")  
    photo_url: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(32))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    locale: Mapped[str] = mapped_column(String(16), default="en")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    department: Mapped[str] = mapped_column(String(120), default="", server_default="", index=True)
    avatar_initials: Mapped[str] = mapped_column(String(8), default="", server_default="")
    title: Mapped[str] = mapped_column(String(200), default="", server_default="")
    external_id: Mapped[str | None] = mapped_column(String(40))  
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def name(self) -> str:
        return self.full_name

    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="UserRole.user_id"
    )
    preferences: Mapped[UserPreferences | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Role(UUIDPk, Timestamps, Base):
    __tablename__ = "roles"

    __table_args__ = (UniqueConstraint("institution_id", "key"),)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("institutions.id"))
    key: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    default_scope: Mapped[str] = mapped_column(String(20), default="institution")

    capabilities: Mapped[list[RoleCapability]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class PermissionOverride(Timestamps, Base):
    __tablename__ = "permission_overrides"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), primary_key=True
    )
    role_key: Mapped[str] = mapped_column(String(60), primary_key=True)
    overrides: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class RoleCapability(Base):
    __tablename__ = "role_capabilities"

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    capability: Mapped[str] = mapped_column(String(60), primary_key=True)


class UserRole(UUIDPk, Timestamps, Base):
    __tablename__ = "user_roles"

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id"),
        Index("ix_user_roles_scope", "scope_type", "scope_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    scope_type: Mapped[str] = mapped_column(String(20))
    scope_id: Mapped[uuid.UUID | None] = mapped_column()
    granted_capabilities: Mapped[list[str] | None] = mapped_column(JSON)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    user: Mapped[User] = relationship(back_populates="roles", foreign_keys=[user_id])
    role: Mapped[Role] = relationship(lazy="joined")


class UserPreferences(Timestamps, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    channels: Mapped[dict[str, bool]] = mapped_column(
        JSON, default=lambda: {"in_app": True, "email": True, "sms": False, "push": False}
    )

    events: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5))  
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5))  
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
    advisor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class GuardianLink(UUIDPk, Timestamps, Base):
    __tablename__ = "guardian_links"

    __table_args__ = (UniqueConstraint("guardian_id", "student_id"),)
    guardian_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    student_consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permitted_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    notify: Mapped[bool] = mapped_column(Boolean, default=False)
    invite_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("guardian_invites.id", ondelete="SET NULL"))


class GuardianInvite(UUIDPk, Timestamps, Base):
    __tablename__ = "guardian_invites"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    code_hint: Mapped[str] = mapped_column(String(8))
    guardian_email: Mapped[str] = mapped_column(String(320), default="", server_default="")
    relation: Mapped[str] = mapped_column(String(40), default="", server_default="")
    permitted_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    notify: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))