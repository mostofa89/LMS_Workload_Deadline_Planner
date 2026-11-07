from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Generator, Union

import sqlalchemy.util.typing as sa_typing

# Python 3.14 compatibility patch for SQLAlchemy 2.0.40 Union.__getitem__ issue
try:
    Union.__getitem__((str, int))
except TypeError:
    def _py314_make_union_type(*types):
        if len(types) == 1:
            return types[0]
        return Union[tuple(types)]
    sa_typing.make_union_type = _py314_make_union_type

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


connect_args: dict[str, Any] = {}
engine_kwargs: dict[str, Any] = {"echo": False}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }
    )

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class UUIDPk:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
