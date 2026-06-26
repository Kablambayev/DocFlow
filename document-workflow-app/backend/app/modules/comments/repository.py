from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.comments.models import CommentType, DocumentComment
from app.modules.documents.models import Document
from app.modules.users.models import User
from app.modules.workflow.models import ApprovalDecision, ApprovalProcess, ApprovalTask


class CommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_document(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def get_comment(self, comment_id: UUID) -> DocumentComment | None:
        return self.db.get(DocumentComment, comment_id)

    def get_user_name(self, user_id: UUID | None) -> str | None:
        if user_id is None:
            return None
        user = self.db.get(User, user_id)
        return user.full_name if user else None

    def user_has_document_task(self, document_id: UUID, user_id: UUID) -> bool:
        return self.db.scalar(select(ApprovalTask.id).where(ApprovalTask.document_id == document_id, ApprovalTask.approver_id == user_id)) is not None

    def list_comments(self, document_id: UUID) -> list[DocumentComment]:
        return list(
            self.db.scalars(
                select(DocumentComment)
                .where(DocumentComment.document_id == document_id, DocumentComment.is_deleted.is_(False))
                .order_by(DocumentComment.created_at.asc())
            )
        )

    def create_comment(self, document_id: UUID, author_id: UUID, text: str, comment_type: str = CommentType.GENERAL, parent_comment_id: UUID | None = None) -> DocumentComment:
        comment = DocumentComment(
            document_id=document_id,
            author_id=author_id,
            comment_text=text,
            comment_type=comment_type,
            parent_comment_id=parent_comment_id,
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def update_comment(self, comment: DocumentComment, text: str) -> DocumentComment:
        comment.comment_text = text
        comment.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def soft_delete_comment(self, comment: DocumentComment, user_id: UUID) -> DocumentComment:
        comment.is_deleted = True
        comment.deleted_by = user_id
        comment.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def list_audit_for_document(self, document_id: UUID) -> list[AuditLog]:
        return list(
            self.db.scalars(
                select(AuditLog)
                .where(
                    (AuditLog.entity_type == "document") & (AuditLog.entity_id == document_id)
                    | (AuditLog.new_values_json["document_id"].as_string() == str(document_id))
                    | (AuditLog.old_values_json["document_id"].as_string() == str(document_id))
                )
                .order_by(AuditLog.created_at.asc())
            )
        )

    def list_decisions_for_document(self, document_id: UUID) -> list[ApprovalDecision]:
        return list(self.db.scalars(select(ApprovalDecision).where(ApprovalDecision.document_id == document_id).order_by(ApprovalDecision.created_at.asc())))

    def list_processes_for_document(self, document_id: UUID) -> list[ApprovalProcess]:
        return list(self.db.scalars(select(ApprovalProcess).where(ApprovalProcess.document_id == document_id).order_by(ApprovalProcess.started_at.desc())))

    def list_tasks_for_process(self, process_id: UUID) -> list[ApprovalTask]:
        return list(self.db.scalars(select(ApprovalTask).where(ApprovalTask.process_id == process_id).order_by(ApprovalTask.step_order.asc(), ApprovalTask.created_at.asc())))
