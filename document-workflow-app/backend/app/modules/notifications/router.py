from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import (
    MarkAllNotificationsReadResponse,
    MarkNotificationReadResponse,
    NotificationsResponse,
    UnreadCountResponse,
)
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


@router.get("/my", response_model=NotificationsResponse)
def get_my_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    is_read: bool | None = None,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
):
    return service.get_my_notifications(current_user, limit=limit, offset=offset, is_read=is_read)


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(current_user: User = Depends(get_current_user), service: NotificationService = Depends(get_service)):
    return UnreadCountResponse(unread_count=service.get_unread_count(current_user))


@router.post("/{notification_id}/read", response_model=MarkNotificationReadResponse)
def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
):
    service.mark_as_read(notification_id, current_user)
    return MarkNotificationReadResponse()


@router.post("/read-all", response_model=MarkAllNotificationsReadResponse)
def mark_all_notifications_read(current_user: User = Depends(get_current_user), service: NotificationService = Depends(get_service)):
    return MarkAllNotificationsReadResponse(updated_count=service.mark_all_as_read(current_user))
