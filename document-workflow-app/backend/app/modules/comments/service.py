from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.comments.models import CommentType
from app.modules.comments.repository import CommentRepository
from app.modules.comments.schemas import (
    ApprovalProcessTimelineRead,
    ApprovalStepTimelineRead,
    ApprovalTaskTimelineRead,
    ApprovalTimelineRead,
    DocumentCommentCreate,
    DocumentCommentRead,
    DocumentCommentUpdate,
    TimelineItem,
)
from app.modules.notifications.models import NotificationType
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User


class CommentService:
    def __init__(self, repository: CommentRepository):
        self.repository = repository
        self.audit_service = AuditService(AuditRepository(self.repository.db))
        self.notification_service = NotificationService(NotificationRepository(self.repository.db))

    def list_comments(self, document_id: UUID, user: User) -> list[DocumentCommentRead]:
        document = self._get_document(document_id)
        self._require_permission(user.id, "document_comment.read")
        self._ensure_can_access_document(document, user.id)
        return [self._read(comment) for comment in self.repository.list_comments(document_id)]

    def create_comment(self, document_id: UUID, payload: DocumentCommentCreate, user: User) -> DocumentCommentRead:
        document = self._get_document(document_id)
        self._require_permission(user.id, "document_comment.create")
        self._ensure_can_access_document(document, user.id)
        text = payload.comment_text.strip()
        if not text:
            raise AppError("Comment is required", code="COMMENT_REQUIRED", status_code=422)
        comment = self.repository.create_comment(document_id, user.id, text, CommentType.GENERAL, payload.parent_comment_id)
        self.audit_service.log("document_comment", comment.id, "document_comment_created", user_id=user.id, new_values_json={"document_id": str(document_id), "comment_id": str(comment.id)})
        self._notify_general_comment(document, comment, user)
        self.repository.db.commit()
        return self._read(comment)

    def update_comment(self, comment_id: UUID, payload: DocumentCommentUpdate, user: User) -> DocumentCommentRead:
        comment = self._get_comment(comment_id)
        self._require_permission(user.id, "document_comment.update")
        self._ensure_general_comment(comment)
        if comment.author_id != user.id and not self._is_admin(user.id):
            raise AppError("Comment access denied", code="COMMENT_ACCESS_DENIED", status_code=403)
        document = self._get_document(comment.document_id)
        self._ensure_can_access_document(document, user.id)
        text = payload.comment_text.strip()
        if not text:
            raise AppError("Comment is required", code="COMMENT_REQUIRED", status_code=422)
        updated = self.repository.update_comment(comment, text)
        self.audit_service.log("document_comment", updated.id, "document_comment_updated", user_id=user.id, new_values_json={"document_id": str(updated.document_id), "comment_id": str(updated.id)})
        self.repository.db.commit()
        return self._read(updated)

    def delete_comment(self, comment_id: UUID, user: User) -> None:
        comment = self._get_comment(comment_id)
        self._require_permission(user.id, "document_comment.delete")
        self._ensure_general_comment(comment)
        if comment.author_id != user.id and not self._is_admin(user.id):
            raise AppError("Comment access denied", code="COMMENT_ACCESS_DENIED", status_code=403)
        document = self._get_document(comment.document_id)
        self._ensure_can_access_document(document, user.id)
        self.repository.soft_delete_comment(comment, user.id)
        self.audit_service.log("document_comment", comment.id, "document_comment_deleted", user_id=user.id, old_values_json={"document_id": str(comment.document_id), "comment_id": str(comment.id)})
        self.repository.db.commit()

    def get_document_timeline(self, document_id: UUID, user: User) -> list[TimelineItem]:
        document = self._get_document(document_id)
        self._require_permission(user.id, "document.read")
        self._ensure_can_access_document(document, user.id)
        items: list[TimelineItem] = []
        for audit in self.repository.list_audit_for_document(document_id):
            items.append(
                TimelineItem(
                    id=str(audit.id),
                    type=self._normalize_audit_type(audit.action),
                    title=audit.action,
                    description=None,
                    user_id=audit.user_id,
                    user_name=self.repository.get_user_name(audit.user_id),
                    created_at=audit.created_at,
                    payload={"old": audit.old_values_json or {}, "new": audit.new_values_json or {}},
                )
            )
        for comment in self.repository.list_comments(document_id):
            items.append(
                TimelineItem(
                    id=str(comment.id),
                    type="comment_added",
                    title="Комментарий добавлен",
                    description=comment.comment_text,
                    user_id=comment.author_id,
                    user_name=self.repository.get_user_name(comment.author_id),
                    created_at=comment.created_at,
                    payload={"comment_type": comment.comment_type},
                )
            )
        return sorted(items, key=lambda item: item.created_at)

    def get_approval_timeline(self, document_id: UUID, user: User) -> ApprovalTimelineRead:
        document = self._get_document(document_id)
        self._require_permission(user.id, "document.read")
        self._ensure_can_access_document(document, user.id)
        processes = self.repository.list_processes_for_document(document_id)
        if not processes:
            return ApprovalTimelineRead(process=None, steps=[])
        process = processes[0]
        tasks = self.repository.list_tasks_for_process(process.id)
        decisions_by_task = {decision.task_id: decision for decision in self.repository.list_decisions_for_document(document_id)}
        grouped: dict[int, list] = {}
        for task in tasks:
            grouped.setdefault(task.step_order, []).append(task)
        steps = []
        for order, step_tasks in sorted(grouped.items()):
            statuses = [task.status for task in step_tasks]
            if "Rejected" in statuses:
                status = "Rejected"
            elif "Pending" in statuses:
                status = "Pending"
            elif all(item == "Approved" for item in statuses):
                status = "Approved"
            elif "Cancelled" in statuses:
                status = "Cancelled"
            else:
                status = statuses[0] if statuses else "Pending"
            steps.append(
                ApprovalStepTimelineRead(
                    step_order=order,
                    step_name=step_tasks[0].step_name,
                    status=status,
                    tasks=[
                        ApprovalTaskTimelineRead(
                            id=task.id,
                            approver_id=task.approver_id,
                            approver_name=self.repository.get_user_name(task.approver_id),
                            status=task.status,
                            created_at=task.created_at,
                            completed_at=task.completed_at,
                            comment=decisions_by_task.get(task.id).comment if task.id in decisions_by_task else None,
                        )
                        for task in step_tasks
                    ],
                )
            )
        return ApprovalTimelineRead(
            process=ApprovalProcessTimelineRead(id=process.id, status=process.status, started_at=process.started_at, finished_at=process.finished_at),
            steps=steps,
        )

    def _read(self, comment) -> DocumentCommentRead:
        return DocumentCommentRead.model_validate(comment).model_copy(update={"author_name": self.repository.get_user_name(comment.author_id)})

    def _get_document(self, document_id: UUID):
        document = self.repository.get_document(document_id)
        if document is None:
            raise AppError("Document not found", code="DOCUMENT_NOT_FOUND", status_code=404)
        return document

    def _get_comment(self, comment_id: UUID):
        comment = self.repository.get_comment(comment_id)
        if comment is None or comment.is_deleted:
            raise AppError("Comment not found", code="COMMENT_NOT_FOUND", status_code=404)
        return comment

    def _permissions(self, user_id: UUID) -> set[str]:
        return get_user_permission_codes(self.repository.db, user_id)

    def _is_admin(self, user_id: UUID) -> bool:
        return "admin.access" in self._permissions(user_id)

    def _require_permission(self, user_id: UUID, permission_code: str) -> None:
        permissions = self._permissions(user_id)
        if "admin.access" not in permissions and permission_code not in permissions:
            raise AppError("Permission required", code="PERMISSION_DENIED", status_code=403, details={"permission": permission_code})

    def _ensure_can_access_document(self, document, user_id: UUID) -> None:
        if self._is_admin(user_id) or document.author_id == user_id or self.repository.user_has_document_task(document.id, user_id):
            return
        raise AppError("Document access denied", code="DOCUMENT_ACCESS_DENIED", status_code=403)

    def _ensure_general_comment(self, comment) -> None:
        if comment.comment_type != CommentType.GENERAL:
            raise AppError("Only general comments can be changed", code="COMMENT_CHANGE_FORBIDDEN", status_code=403)

    def _normalize_audit_type(self, action: str) -> str:
        if action == "document_file_uploaded":
            return "file_uploaded"
        if action == "document_file_deleted":
            return "file_deleted"
        return action

    def _notify_general_comment(self, document, comment, user: User) -> None:
        approver_ids = set(self.notification_service.approver_ids_for_document(document.id))
        recipients = approver_ids if user.id == document.author_id else approver_ids | {document.author_id}
        recipients.discard(user.id)
        actor_name = self.repository.get_user_name(user.id) or "Пользователь"
        self.notification_service.safe_notify_users(
            recipients,
            actor_id=user.id,
            notification_type=NotificationType.DOCUMENT_COMMENT_CREATED,
            title="Новый комментарий",
            message=f"{actor_name} добавил комментарий к документу {document.number}",
            entity_type="comment",
            entity_id=comment.id,
            document_id=document.id,
            payload={"document_number": document.number, "document_title": document.title},
        )
