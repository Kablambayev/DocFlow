from __future__ import annotations

from uuid import UUID

from fastapi import Header


def get_current_user_id(x_user_id: str | None = Header(default=None)) -> UUID | None:
    if x_user_id is None:
        return None
    return UUID(x_user_id)
