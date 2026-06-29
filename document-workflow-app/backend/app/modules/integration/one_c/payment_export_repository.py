from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from app.modules.document_types.models import DocumentType
from app.modules.documents.models import Document
from app.modules.integration.one_c.payment_export_models import PaymentRequest1CExport
from app.modules.users.models import User
from app.modules.workflow.models import ApprovalDecision, ApprovalProcess


class PaymentRequest1CExportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_document_id(self, document_id: UUID) -> PaymentRequest1CExport | None:
        stmt: Select[tuple[PaymentRequest1CExport]] = select(PaymentRequest1CExport).where(
            PaymentRequest1CExport.document_id == document_id
        )
        return self.db.scalar(stmt)

    def get_document(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def get_document_type(self, document_type_id: UUID) -> DocumentType | None:
        return self.db.get(DocumentType, document_type_id)

    def get_user(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def create(self, **values) -> PaymentRequest1CExport:
        item = PaymentRequest1CExport(**values)
        self.db.add(item)
        self.db.flush()
        return item

    def save(self, item: PaymentRequest1CExport) -> PaymentRequest1CExport:
        self.db.add(item)
        self.db.flush()
        return item

    def get_approval_process_finished_at(self, document_id: UUID) -> datetime | None:
        stmt = (
            select(ApprovalProcess.finished_at)
            .where(ApprovalProcess.document_id == document_id, ApprovalProcess.finished_at.is_not(None))
            .order_by(desc(ApprovalProcess.finished_at))
        )
        return self.db.scalar(stmt)

    def get_last_approval_decision_at(self, document_id: UUID) -> datetime | None:
        stmt = (
            select(ApprovalDecision.created_at)
            .where(ApprovalDecision.document_id == document_id, ApprovalDecision.decision == "Approve")
            .order_by(desc(ApprovalDecision.created_at))
        )
        return self.db.scalar(stmt)