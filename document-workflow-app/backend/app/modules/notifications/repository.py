from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification
from app.modules.users.models import User
from app.modules.workflow.models import ApprovalTask


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, notification_id: UUID) -> Notification | None:
        return self.db.get(Notification, notification_id)

    def get_user_name(self, user_id: UUID | None) -> str | None:
        if user_id is None:
            return None
        user = self.db.get(User, user_id)
        return user.full_name if user else None

    def create(self, **values) -> Notification:
        notification = Notification(**values)
        self.db.add(notification)
        self.db.flush()
        return notification

    def find_duplicate(
        self,
        *,
        recipient_id: UUID,
        notification_type: str,
        entity_id: UUID | None,
        document_id: UUID | None,
        task_id: UUID | None,
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.recipient_id == recipient_id,
            Notification.type == notification_type,
            Notification.entity_id == entity_id,
            Notification.document_id == document_id,
            Notification.task_id == task_id,
        )
        return self.db.scalar(stmt)

    def list_for_user(self, user_id: UUID, *, limit: int, offset: int, is_read: bool | None) -> list[Notification]:
        stmt = select(Notification).where(Notification.recipient_id == user_id)
        if is_read is not None:
            stmt = stmt.where(Notification.is_read.is_(is_read))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def count_for_user(self, user_id: UUID, *, is_read: bool | None = None) -> int:
        stmt = select(func.count(Notification.id)).where(Notification.recipient_id == user_id)
        if is_read is not None:
            stmt = stmt.where(Notification.is_read.is_(is_read))
        return int(self.db.scalar(stmt) or 0)

    def unread_count(self, user_id: UUID) -> int:
        return self.count_for_user(user_id, is_read=False)

    def mark_as_read(self, notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            self.db.flush()
        return notification

    def mark_all_as_read(self, user_id: UUID) -> int:
        unread = list(
            self.db.scalars(
                select(Notification).where(Notification.recipient_id == user_id, Notification.is_read.is_(False))
            )
        )
        now = datetime.now(timezone.utc)
        for notification in unread:
            notification.is_read = True
            notification.read_at = now
        self.db.flush()
        return len(unread)

    def list_task_approver_ids_for_document(self, document_id: UUID) -> list[UUID]:
        return list(
            self.db.scalars(
                select(ApprovalTask.approver_id)
                .where(ApprovalTask.document_id == document_id)
                .distinct()
            )
        )
