from __future__ import annotations

from typing import Union
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

from app.config import get_settings, settings

__all__ = ["get_settings", "settings"]
