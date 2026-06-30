from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.modules.accounting.models import (
    AccountingCashFlowItem,
    AccountingCashFlowOperationType,
    AccountingCurrency,
    AccountingOrganization,
    AccountingProject,
)
from app.modules.document_types.models import DocumentType
from app.modules.documents.models import Document


class BddsReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_cash_flow_allocation_documents(self) -> list[Document]:
        stmt: Select[tuple[Document]] = (
            select(Document)
            .join(DocumentType, DocumentType.id == Document.document_type_id)
            .where(DocumentType.code == "CashFlowAllocation")
            .order_by(Document.created_at.asc(), Document.id.asc())
        )
        return list(self.db.scalars(stmt))

    def get_organization(self, item_id: UUID | None):
        return self.db.get(AccountingOrganization, item_id) if item_id is not None else None

    def get_project(self, item_id: UUID | None):
        return self.db.get(AccountingProject, item_id) if item_id is not None else None

    def get_cash_flow_item(self, item_id: UUID | None):
        return self.db.get(AccountingCashFlowItem, item_id) if item_id is not None else None

    def get_cash_flow_operation_type(self, item_id: UUID | None):
        return self.db.get(AccountingCashFlowOperationType, item_id) if item_id is not None else None

    def get_currency(self, item_id: UUID | None):
        return self.db.get(AccountingCurrency, item_id) if item_id is not None else None
