from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recipient_id: UUID
    actor_id: UUID | None
    actor_name: str | None = None
    type: str
    title: str
    message: str | None
    entity_type: str | None
    entity_id: UUID | None
    document_id: UUID | None
    task_id: UUID | None
    payload: dict
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationsResponse(BaseModel):
    items: list[NotificationRead]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkNotificationReadResponse(BaseModel):
    status: str = "read"


class MarkAllNotificationsReadResponse(BaseModel):
    status: str = "read_all"
    updated_count: int
