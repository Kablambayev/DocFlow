from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.documents.models import Document
from app.modules.files.models import DocumentFile
from app.modules.workflow.models import ApprovalTask


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_document(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def user_has_document_task(self, document_id: UUID, user_id: UUID) -> bool:
        stmt = select(ApprovalTask.id).where(
            ApprovalTask.document_id == document_id,
            ApprovalTask.approver_id == user_id,
        )
        return self.db.scalar(stmt) is not None

    def list_for_document(self, document_id: UUID) -> list[DocumentFile]:
        stmt = (
            select(DocumentFile)
            .where(DocumentFile.document_id == document_id, DocumentFile.is_deleted.is_(False))
            .order_by(DocumentFile.uploaded_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_file(self, file_id: UUID) -> DocumentFile | None:
        return self.db.get(DocumentFile, file_id)

    def create_file(
        self,
        *,
        file_id: UUID,
        document_id: UUID,
        field_code: str | None,
        file_name: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
        uploaded_by: UUID,
    ) -> DocumentFile:
        item = DocumentFile(
            id=file_id,
            document_id=document_id,
            field_code=field_code,
            file_name=file_name,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
            uploaded_by=uploaded_by,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def soft_delete(self, item: DocumentFile, user_id: UUID) -> DocumentFile:
        item.is_deleted = True
        item.deleted_by = user_id
        item.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item
