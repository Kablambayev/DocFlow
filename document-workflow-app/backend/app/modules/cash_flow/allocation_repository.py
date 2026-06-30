from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.accounting.models import (
    AccountingCashFlowItem,
    AccountingCashFlowOperationType,
    AccountingCounterparty,
    AccountingCounterpartyContract,
    AccountingCurrency,
    AccountingOrganization,
    AccountingProject,
)
from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.documents.models import Document, DocumentApprovalStatus
from app.modules.users.models import User


class CashFlowAllocationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_cash_flow_allocation_document_type_and_version(self) -> tuple[DocumentType, DocumentTypeVersion]:
        document_type = self.db.scalar(select(DocumentType).where(DocumentType.code == "CashFlowAllocation"))
        if document_type is None:
            raise AppError("CashFlowAllocation document type not found", code="DOCUMENT_TYPE_NOT_FOUND", status_code=404)
        version = self.db.scalar(
            select(DocumentTypeVersion).where(
                DocumentTypeVersion.document_type_id == document_type.id,
                DocumentTypeVersion.status == VersionStatus.PUBLISHED,
            )
        )
        if version is None:
            raise AppError("CashFlowAllocation published version not found", code="DOCUMENT_TYPE_VERSION_NOT_FOUND", status_code=404)
        return document_type, version

    def list_allocation_documents(self) -> list[Document]:
        stmt: Select[tuple[Document]] = (
            select(Document)
            .join(DocumentType, DocumentType.id == Document.document_type_id)
            .where(DocumentType.code == "CashFlowAllocation")
            .order_by(Document.document_date.desc(), Document.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_allocation_document(self, document_id: UUID) -> Document | None:
        stmt: Select[tuple[Document]] = (
            select(Document)
            .join(DocumentType, DocumentType.id == Document.document_type_id)
            .where(Document.id == document_id, DocumentType.code == "CashFlowAllocation")
        )
        return self.db.scalar(stmt)

    def find_allocation_by_source_identity(
        self,
        *,
        source_system: str,
        source_document_type_1c: str,
        source_document_external_id: str,
    ) -> Document | None:
        stmt: Select[tuple[Document]] = (
            select(Document)
            .join(DocumentType, DocumentType.id == Document.document_type_id)
            .where(
                DocumentType.code == "CashFlowAllocation",
                Document.data_json["source_system"].astext == source_system,
                Document.data_json["source_document_type_1c"].astext == source_document_type_1c,
                Document.data_json["source_document_external_id"].astext == source_document_external_id,
            )
        )
        return self.db.scalar(stmt)

    def create_cash_flow_allocation_document(
        self,
        *,
        document_type_id: UUID,
        document_type_version_id: UUID,
        author_id: UUID,
        number: str,
        title: str,
        document_date: datetime,
        data_json: dict,
    ) -> Document:
        document = Document(
            document_type_id=document_type_id,
            document_type_version_id=document_type_version_id,
            number=number,
            document_date=document_date,
            author_id=author_id,
            organization_id=None,
            department_id=None,
            approval_status=DocumentApprovalStatus.DRAFT,
            business_status=None,
            title=title,
            data_json=data_json,
        )
        self.db.add(document)
        self.db.flush()
        return document

    def save_document(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def generate_document_number(self, prefix: str = "CFA") -> str:
        year = datetime.now(timezone.utc).year
        pattern = f"{prefix}-{year}-%"
        max_number = 0
        for value in self.db.scalars(select(Document.number).where(Document.number.like(pattern))):
            parts = value.split("-")
            if len(parts) == 3 and parts[2].isdigit():
                max_number = max(max_number, int(parts[2]))
        return f"{prefix}-{year}-{max_number + 1:06d}"

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

    def get_cash_flow_item(self, item_id: UUID | None):
        return self.db.get(AccountingCashFlowItem, item_id) if item_id is not None else None

    def get_cash_flow_operation_type(self, item_id: UUID | None):
        return self.db.get(AccountingCashFlowOperationType, item_id) if item_id is not None else None

    def get_user(self, item_id: UUID | None):
        return self.db.get(User, item_id) if item_id is not None else None
