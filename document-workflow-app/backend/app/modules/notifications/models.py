from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class NotificationType(StrEnum):
    APPROVAL_TASK_CREATED = "approval_task_created"
    APPROVAL_TASK_CANCELLED = "approval_task_cancelled"
    APPROVAL_TASK_APPROVED = "approval_task_approved"
    APPROVAL_TASK_REJECTED = "approval_task_rejected"
    DOCUMENT_SUBMITTED = "document_submitted"
    DOCUMENT_APPROVED = "document_approved"
    DOCUMENT_REJECTED = "document_rejected"
    DOCUMENT_WITHDRAWN = "document_withdrawn"
    DOCUMENT_COMMENT_CREATED = "document_comment_created"
    DOCUMENT_FILE_UPLOADED = "document_file_uploaded"


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_recipient_created_at", "recipient_id", "created_at"),
        Index("idx_notifications_recipient_is_read", "recipient_id", "is_read"),
        Index("idx_notifications_document_id", "document_id"),
        Index("idx_notifications_task_id", "task_id"),
    )

    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[UUID | None] = mapped_column()
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("approval_tasks.id", ondelete="CASCADE"))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
