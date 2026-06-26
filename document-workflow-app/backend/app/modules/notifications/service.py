from __future__ import annotations

import logging
from uuid import UUID

from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import NotificationRead, NotificationsResponse
from app.modules.users.models import User

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self.repository = repository

    def create_notification(
        self,
        *,
        recipient_id: UUID,
        actor_id: UUID | None,
        notification_type: str,
        title: str,
        message: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        document_id: UUID | None = None,
        task_id: UUID | None = None,
        payload: dict | None = None,
        skip_self: bool = True,
        dedupe: bool = True,
    ) -> Notification | None:
        if skip_self and actor_id is not None and recipient_id == actor_id:
            return None
        if dedupe and self.repository.find_duplicate(
            recipient_id=recipient_id,
            notification_type=notification_type,
            entity_id=entity_id,
            document_id=document_id,
            task_id=task_id,
        ):
            return None
        return self.repository.create(
            recipient_id=recipient_id,
            actor_id=actor_id,
            type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            document_id=document_id,
            task_id=task_id,
            payload=payload or {},
        )

    def create_many(self, recipient_ids: list[UUID] | set[UUID], **kwargs) -> list[Notification]:
        created: list[Notification] = []
        for recipient_id in set(recipient_ids):
            notification = self.create_notification(recipient_id=recipient_id, **kwargs)
            if notification is not None:
                created.append(notification)
        return created

    def notify_document_author(self, document, **kwargs) -> Notification | None:
        return self.create_notification(recipient_id=document.author_id, document_id=document.id, **kwargs)

    def notify_task_approver(self, task, **kwargs) -> Notification | None:
        return self.create_notification(
            recipient_id=task.approver_id,
            document_id=task.document_id,
            task_id=task.id,
            entity_type=kwargs.pop("entity_type", "task"),
            entity_id=kwargs.pop("entity_id", task.id),
            **kwargs,
        )

    def notify_users(self, user_ids: list[UUID] | set[UUID], **kwargs) -> list[Notification]:
        return self.create_many(user_ids, **kwargs)

    def safe_create_notification(self, **kwargs) -> Notification | None:
        try:
            return self.create_notification(**kwargs)
        except Exception:
            logger.exception("Failed to create notification")
            return None

    def safe_notify_users(self, user_ids: list[UUID] | set[UUID], **kwargs) -> list[Notification]:
        try:
            return self.notify_users(user_ids, **kwargs)
        except Exception:
            logger.exception("Failed to create notifications")
            return []

    def get_my_notifications(self, user: User, *, limit: int, offset: int, is_read: bool | None) -> NotificationsResponse:
        self._require_permission(user.id, "notification.read")
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        items = self.repository.list_for_user(user.id, limit=limit, offset=offset, is_read=is_read)
        return NotificationsResponse(
            items=[self._read(item) for item in items],
            total=self.repository.count_for_user(user.id, is_read=is_read),
            unread_count=self.repository.unread_count(user.id),
        )

    def get_unread_count(self, user: User) -> int:
        self._require_permission(user.id, "notification.read")
        return self.repository.unread_count(user.id)

    def mark_as_read(self, notification_id: UUID, user: User) -> None:
        self._require_permission(user.id, "notification.update")
        notification = self.repository.get(notification_id)
        if notification is None:
            raise AppError("Notification not found", code="NOTIFICATION_NOT_FOUND", status_code=404)
        if notification.recipient_id != user.id:
            raise AppError("Notification access denied", code="NOTIFICATION_ACCESS_DENIED", status_code=403)
        self.repository.mark_as_read(notification)
        self.repository.db.commit()

    def mark_all_as_read(self, user: User) -> int:
        self._require_permission(user.id, "notification.update")
        count = self.repository.mark_all_as_read(user.id)
        self.repository.db.commit()
        return count

    def approver_ids_for_document(self, document_id: UUID) -> list[UUID]:
        return self.repository.list_task_approver_ids_for_document(document_id)

    def _read(self, notification: Notification) -> NotificationRead:
        return NotificationRead.model_validate(notification).model_copy(
            update={"actor_name": self.repository.get_user_name(notification.actor_id)}
        )

    def _permissions(self, user_id: UUID) -> set[str]:
        return get_user_permission_codes(self.repository.db, user_id)

    def _require_permission(self, user_id: UUID, permission_code: str) -> None:
        permissions = self._permissions(user_id)
        if "admin.access" not in permissions and permission_code not in permissions:
            raise AppError("Permission required", code="PERMISSION_DENIED", status_code=403, details={"permission": permission_code})
