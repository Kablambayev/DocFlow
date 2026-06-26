from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.documents.models import Document, DocumentApprovalStatus
from app.modules.documents.schemas import DocumentCreate, DocumentUpdate
from app.modules.workflow.models import (
    ApprovalProcess,
    ApprovalRoute,
    ApprovalRouteVersion,
    ApprovalTask,
    ProcessStatus,
    TaskStatus,
)


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Document]:
        stmt: Select[tuple[Document]] = select(Document).order_by(Document.created_at.desc())
        return list(self.db.scalars(stmt))

    def list_visible_for_user(self, user_id: UUID) -> list[Document]:
        stmt = (
            select(Document)
            .outerjoin(ApprovalTask, ApprovalTask.document_id == Document.id)
            .where(or_(Document.author_id == user_id, ApprovalTask.approver_id == user_id))
            .distinct()
            .order_by(Document.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def user_has_task_for_document(self, document_id: UUID, user_id: UUID) -> bool:
        stmt = select(ApprovalTask.id).where(
            ApprovalTask.document_id == document_id,
            ApprovalTask.approver_id == user_id,
        )
        return self.db.scalar(stmt) is not None

    def create(self, payload: DocumentCreate) -> Document:
        doc = Document(
            document_type_id=payload.document_type_id,
            document_type_version_id=payload.document_type_version_id,
            number=payload.number,
            document_date=payload.document_date,
            author_id=payload.author_id,
            organization_id=payload.organization_id,
            department_id=payload.department_id,
            approval_status=DocumentApprovalStatus.DRAFT,
            business_status=None,
            title=payload.title,
            data_json=payload.data_json or {},
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update(self, doc: Document, payload: DocumentUpdate) -> Document:
        update_data = payload.model_dump(exclude_unset=True)
        if "data_json" in update_data and update_data["data_json"] is None:
            update_data["data_json"] = {}

        for key, value in update_data.items():
            setattr(doc, key, value)

        self.db.commit()
        self.db.refresh(doc)
        return doc

    def set_status(self, doc: Document, status: DocumentApprovalStatus) -> Document:
        doc.approval_status = status
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_document_type(self, document_type_id: UUID) -> DocumentType | None:
        return self.db.get(DocumentType, document_type_id)

    def get_document_type_version(self, version_id: UUID) -> DocumentTypeVersion | None:
        return self.db.get(DocumentTypeVersion, version_id)

    def get_active_process(self, document_id: UUID) -> ApprovalProcess | None:
        stmt = select(ApprovalProcess).where(
            ApprovalProcess.document_id == document_id,
            ApprovalProcess.status == ProcessStatus.RUNNING,
        )
        return self.db.scalar(stmt)

    def cancel_process_and_tasks(self, process: ApprovalProcess) -> None:
        process.status = ProcessStatus.CANCELLED
        process.finished_at = datetime.now(timezone.utc)

        pending_tasks = list(
            self.db.scalars(
                select(ApprovalTask).where(ApprovalTask.process_id == process.id, ApprovalTask.status == TaskStatus.PENDING)
            )
        )
        for task in pending_tasks:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)

    def get_published_route_version_for_route(self, route_id: UUID) -> ApprovalRouteVersion | None:
        stmt = (
            select(ApprovalRouteVersion)
            .where(ApprovalRouteVersion.route_id == route_id, ApprovalRouteVersion.status == VersionStatus.PUBLISHED)
            .order_by(ApprovalRouteVersion.version_number.desc())
        )
        return self.db.scalar(stmt)

    def get_routes_for_document_type(self, document_type_id: UUID) -> list[ApprovalRoute]:
        return list(
            self.db.scalars(
                select(ApprovalRoute).where(ApprovalRoute.document_type_id == document_type_id, ApprovalRoute.is_active.is_(True))
            )
        )

