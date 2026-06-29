from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.modules.accounting.models import (
    AccountingCounterparty,
    AccountingCounterpartyContract,
    AccountingCurrency,
    AccountingExpenseItem,
    AccountingOrganization,
    AccountingProject,
)
from app.modules.document_types.models import DocumentType
from app.modules.documents.models import Document
from app.modules.integration.one_c.payment_export_models import PaymentRequest1CExport
from app.modules.workflow.models import ApprovalDecision, ApprovalProcess


class TreasuryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_payment_request_documents(self, approval_status: str) -> list[Document]:
        stmt: Select[tuple[Document]] = (
            select(Document)
            .join(DocumentType, DocumentType.id == Document.document_type_id)
            .where(DocumentType.code == "PaymentRequest", Document.approval_status == approval_status)
            .order_by(Document.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_exports_by_document_ids(self, document_ids: list[UUID]) -> dict[UUID, PaymentRequest1CExport]:
        if not document_ids:
            return {}
        stmt: Select[tuple[PaymentRequest1CExport]] = select(PaymentRequest1CExport).where(
            PaymentRequest1CExport.document_id.in_(document_ids)
        )
        return {item.document_id: item for item in self.db.scalars(stmt)}

    def get_approved_at_by_document_ids(self, documents: list[Document]) -> dict[UUID, datetime]:
        document_ids = [document.id for document in documents]
        if not document_ids:
            return {}

        process_rows = self.db.execute(
            select(ApprovalProcess.document_id, ApprovalProcess.finished_at)
            .where(ApprovalProcess.document_id.in_(document_ids), ApprovalProcess.finished_at.is_not(None))
            .order_by(ApprovalProcess.finished_at.desc())
        )
        process_dates: dict[UUID, datetime] = {}
        for document_id, finished_at in process_rows:
            process_dates.setdefault(document_id, finished_at)

        decision_rows = self.db.execute(
            select(ApprovalDecision.document_id, ApprovalDecision.created_at)
            .where(ApprovalDecision.document_id.in_(document_ids), ApprovalDecision.decision == "Approve")
            .order_by(ApprovalDecision.created_at.desc())
        )
        decision_dates: dict[UUID, datetime] = {}
        for document_id, created_at in decision_rows:
            decision_dates.setdefault(document_id, created_at)

        return {
            document.id: process_dates.get(document.id) or decision_dates.get(document.id) or document.updated_at
            for document in documents
        }

    def get_organizations(self, item_ids: set[UUID]):
        return self._get_items_by_ids(AccountingOrganization, item_ids)

    def get_counterparties(self, item_ids: set[UUID]):
        return self._get_items_by_ids(AccountingCounterparty, item_ids)

    def get_contracts(self, item_ids: set[UUID]):
        return self._get_items_by_ids(AccountingCounterpartyContract, item_ids)

    def get_currencies(self, item_ids: set[UUID]):
        return self._get_items_by_ids(AccountingCurrency, item_ids)

    def get_projects(self, item_ids: set[UUID]):
        return self._get_items_by_ids(AccountingProject, item_ids)

    def get_expense_items(self, item_ids: set[UUID]):
        return self._get_items_by_ids(AccountingExpenseItem, item_ids)

    def _get_items_by_ids(self, model, item_ids: set[UUID]):
        if not item_ids:
            return {}
        return {item.id: item for item in self.db.scalars(select(model).where(model.id.in_(item_ids)))}

    def get_organization(self, item_id: UUID | None):
        return self.db.get(AccountingOrganization, item_id) if item_id is not None else None

    def get_counterparty(self, item_id: UUID | None):
        return self.db.get(AccountingCounterparty, item_id) if item_id is not None else None

    def get_contract(self, item_id: UUID | None):
        return self.db.get(AccountingCounterpartyContract, item_id) if item_id is not None else None

    def get_currency(self, item_id: UUID | None):
        return self.db.get(AccountingCurrency, item_id) if item_id is not None else None

    def get_project(self, item_id: UUID | None):
        return self.db.get(AccountingProject, item_id) if item_id is not None else None

    def get_expense_item(self, item_id: UUID | None):
        return self.db.get(AccountingExpenseItem, item_id) if item_id is not None else None

    @staticmethod
    def parse_uuid(value) -> UUID | None:
        if not isinstance(value, str):
            return None
        try:
            return UUID(value)
        except ValueError:
            return None

    @staticmethod
    def parse_decimal(value) -> Decimal | None:
        if value in [None, ""]:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def parse_date(value) -> date | None:
        if not isinstance(value, str):
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
