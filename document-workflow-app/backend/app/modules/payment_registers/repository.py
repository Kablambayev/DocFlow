from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
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
from app.modules.payment_registers.models import PaymentRegister, PaymentRegisterRow
from app.modules.users.models import User


class PaymentRegisterRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_registers(
        self,
        *,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        organization_id: UUID | None,
        currency_id: UUID | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[PaymentRegister], int]:
        stmt: Select[tuple[PaymentRegister]] = select(PaymentRegister)
        stmt = self._apply_register_filters(
            stmt,
            status=status,
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id,
            currency_id=currency_id,
            search=search,
        )
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(*self._register_ordering(sort_by, sort_order)).limit(limit).offset(offset)
        return list(self.db.scalars(stmt)), total

    def get_register(self, register_id: UUID) -> PaymentRegister | None:
        return self.db.get(PaymentRegister, register_id)

    def create_register(self, **values) -> PaymentRegister:
        item = PaymentRegister(**values)
        self.db.add(item)
        self.db.flush()
        return item

    def save_register(self, register: PaymentRegister) -> PaymentRegister:
        self.db.add(register)
        self.db.flush()
        return register

    def delete_register(self, register: PaymentRegister) -> None:
        self.db.delete(register)
        self.db.flush()

    def list_rows(self, register_id: UUID) -> list[PaymentRegisterRow]:
        stmt: Select[tuple[PaymentRegisterRow]] = (
            select(PaymentRegisterRow)
            .where(PaymentRegisterRow.register_id == register_id)
            .order_by(PaymentRegisterRow.row_number, PaymentRegisterRow.created_at)
        )
        return list(self.db.scalars(stmt))

    def get_row(self, row_id: UUID) -> PaymentRegisterRow | None:
        return self.db.get(PaymentRegisterRow, row_id)

    def create_row(self, **values) -> PaymentRegisterRow:
        item = PaymentRegisterRow(**values)
        self.db.add(item)
        self.db.flush()
        return item

    def save_row(self, row: PaymentRegisterRow) -> PaymentRegisterRow:
        self.db.add(row)
        self.db.flush()
        return row

    def delete_row(self, row: PaymentRegisterRow) -> None:
        self.db.delete(row)
        self.db.flush()

    def get_max_row_number(self, register_id: UUID) -> int:
        stmt = select(func.max(PaymentRegisterRow.row_number)).where(PaymentRegisterRow.register_id == register_id)
        return int(self.db.scalar(stmt) or 0)

    def list_register_numbers(self) -> list[str]:
        stmt = select(PaymentRegister.number).where(PaymentRegister.number.like("REG-%"))
        return list(self.db.scalars(stmt))

    def list_payment_request_documents(self) -> list[Document]:
        stmt: Select[tuple[Document]] = (
            select(Document)
            .join(DocumentType, DocumentType.id == Document.document_type_id)
            .where(DocumentType.code == "PaymentRequest")
            .order_by(Document.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_documents_by_ids(self, document_ids: list[UUID]) -> dict[UUID, Document]:
        if not document_ids:
            return {}
        stmt: Select[tuple[Document]] = select(Document).where(Document.id.in_(document_ids))
        return {item.id: item for item in self.db.scalars(stmt)}

    def get_document_type_codes(self, document_type_ids: set[UUID]) -> dict[UUID, str]:
        if not document_type_ids:
            return {}
        stmt = select(DocumentType.id, DocumentType.code).where(DocumentType.id.in_(document_type_ids))
        return {row_id: code for row_id, code in self.db.execute(stmt)}

    def get_exports_by_document_ids(self, document_ids: list[UUID]) -> dict[UUID, PaymentRequest1CExport]:
        if not document_ids:
            return {}
        stmt: Select[tuple[PaymentRequest1CExport]] = select(PaymentRequest1CExport).where(
            PaymentRequest1CExport.document_id.in_(document_ids)
        )
        return {item.document_id: item for item in self.db.scalars(stmt)}

    def get_active_register_memberships(
        self,
        document_ids: list[UUID],
        *,
        active_statuses: list[str],
        exclude_register_id: UUID | None = None,
    ) -> dict[UUID, PaymentRegisterRow]:
        if not document_ids:
            return {}
        stmt = (
            select(PaymentRegisterRow)
            .join(PaymentRegister, PaymentRegister.id == PaymentRegisterRow.register_id)
            .where(
                PaymentRegisterRow.document_id.in_(document_ids),
                PaymentRegister.status.in_(active_statuses),
            )
        )
        if exclude_register_id is not None:
            stmt = stmt.where(PaymentRegister.id != exclude_register_id)
        return {item.document_id: item for item in self.db.scalars(stmt)}

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

    def get_user(self, item_id: UUID | None):
        return self.db.get(User, item_id) if item_id is not None else None

    def _apply_register_filters(
        self,
        stmt: Select,
        *,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        organization_id: UUID | None,
        currency_id: UUID | None,
        search: str | None,
    ) -> Select:
        if status:
            stmt = stmt.where(PaymentRegister.status == status)
        if date_from is not None:
            stmt = stmt.where(PaymentRegister.date >= date_from)
        if date_to is not None:
            stmt = stmt.where(PaymentRegister.date <= date_to)
        if organization_id is not None:
            stmt = stmt.where(PaymentRegister.organization_id == organization_id)
        if currency_id is not None:
            stmt = stmt.where(PaymentRegister.currency_id == currency_id)
        if search:
            needle = f"%{search.strip()}%"
            if needle != "%%":
                stmt = stmt.where(or_(PaymentRegister.number.ilike(needle), PaymentRegister.comment.ilike(needle)))
        return stmt

    def _register_ordering(self, sort_by: str, sort_order: str):
        direction = sort_order.lower()
        column_map = {
            "number": PaymentRegister.number,
            "date": PaymentRegister.date,
            "status": PaymentRegister.status,
            "total_amount": PaymentRegister.total_amount,
            "created_at": PaymentRegister.created_at,
            "sent_at": PaymentRegister.sent_at,
        }
        column = column_map.get(sort_by, PaymentRegister.date)
        primary = column.asc() if direction == "asc" else column.desc()
        return [primary, PaymentRegister.created_at.desc()]
