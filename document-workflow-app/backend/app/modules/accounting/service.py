from __future__ import annotations

from uuid import UUID

from fastapi import status

from app.core.exceptions import AppError
from app.modules.accounting.repository import AccountingRepository
from app.modules.accounting.schemas import (
    AccountingCashFlowItemCreate,
    AccountingCashFlowItemUpdate,
    AccountingProjectCreate,
    AccountingProjectUpdate,
    CashFlowOperationTypeCreate,
    CashFlowOperationTypeUpdate,
)


class AccountingService:
    def __init__(self, repository: AccountingRepository):
        self.repository = repository

    def list_organizations(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        return self.repository.list_organizations(search, is_active, limit, offset)

    def list_counterparties(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        return self.repository.list_counterparties(search, is_active, limit, offset)

    def list_counterparty_contracts(
        self,
        organization_id: UUID | None,
        counterparty_id: UUID | None,
        search: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ):
        if organization_id is None and counterparty_id is None:
            return []
        return self.repository.list_counterparty_contracts(organization_id, counterparty_id, search, is_active, limit, offset)

    def list_currencies(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        return self.repository.list_currencies(search, is_active, limit, offset)

    def list_expense_items(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        return self.repository.list_expense_items(search, is_active, limit, offset)

    def list_cash_flow_items(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        return self.repository.list_cash_flow_items(search, is_active, limit, offset)

    def create_cash_flow_item(self, payload: AccountingCashFlowItemCreate):
        if payload.code and self.repository.get_cash_flow_item_by_code(payload.code):
            raise AppError("Cash flow item code already exists", code="ACCOUNTING_CODE_EXISTS", status_code=409)
        item = self.repository.create_cash_flow_item(payload)
        self.repository.db.commit()
        self.repository.db.refresh(item)
        return item

    def update_cash_flow_item(self, item_id: UUID, payload: AccountingCashFlowItemUpdate):
        item = self.repository.get_cash_flow_item(item_id)
        if item is None:
            raise AppError("Cash flow item not found", code="ACCOUNTING_NOT_FOUND", status_code=404)
        if payload.code and item.code and payload.code.lower() != item.code.lower():
            existing = self.repository.get_cash_flow_item_by_code(payload.code)
            if existing is not None and existing.id != item.id:
                raise AppError("Cash flow item code already exists", code="ACCOUNTING_CODE_EXISTS", status_code=409)
        updated = self.repository.update_cash_flow_item(item, payload)
        self.repository.db.commit()
        self.repository.db.refresh(updated)
        return updated

    def list_cash_flow_operation_types(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        return self.repository.list_cash_flow_operation_types(search, is_active, limit, offset)

    def create_cash_flow_operation_type(self, payload: CashFlowOperationTypeCreate):
        if self.repository.get_cash_flow_operation_type_by_code(payload.code):
            raise AppError("Cash flow operation type code already exists", code="ACCOUNTING_CODE_EXISTS", status_code=409)
        item = self.repository.create_cash_flow_operation_type(payload)
        self.repository.db.commit()
        self.repository.db.refresh(item)
        return item

    def update_cash_flow_operation_type(self, item_id: UUID, payload: CashFlowOperationTypeUpdate):
        item = self.repository.get_cash_flow_operation_type(item_id)
        if item is None:
            raise AppError("Cash flow operation type not found", code="ACCOUNTING_NOT_FOUND", status_code=404)
        if payload.code and payload.code.lower() != item.code.lower():
            if self.repository.get_cash_flow_operation_type_by_code(payload.code):
                raise AppError("Cash flow operation type code already exists", code="ACCOUNTING_CODE_EXISTS", status_code=409)
        updated = self.repository.update_cash_flow_operation_type(item, payload)
        self.repository.db.commit()
        self.repository.db.refresh(updated)
        return updated

    def soft_delete_cash_flow_operation_type(self, item_id: UUID):
        item = self.repository.get_cash_flow_operation_type(item_id)
        if item is None:
            raise AppError("Cash flow operation type not found", code="ACCOUNTING_NOT_FOUND", status_code=404)
        updated = self.repository.soft_delete_cash_flow_operation_type(item)
        self.repository.db.commit()
        self.repository.db.refresh(updated)
        return updated

    def list_projects(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        return self.repository.list_projects(search, is_active, limit, offset)

    def create_project(self, payload: AccountingProjectCreate):
        if self.repository.get_project_by_code(payload.code):
            raise AppError("Project code already exists", code="ACCOUNTING_CODE_EXISTS", status_code=409)
        item = self.repository.create_project(payload)
        self.repository.db.commit()
        self.repository.db.refresh(item)
        return item

    def update_project(self, item_id: UUID, payload: AccountingProjectUpdate):
        item = self.repository.get_project(item_id)
        if item is None:
            raise AppError("Project not found", code="ACCOUNTING_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)
        if payload.code and payload.code.lower() != item.code.lower():
            if self.repository.get_project_by_code(payload.code):
                raise AppError("Project code already exists", code="ACCOUNTING_CODE_EXISTS", status_code=409)
        updated = self.repository.update_project(item, payload)
        self.repository.db.commit()
        self.repository.db.refresh(updated)
        return updated

    def soft_delete_project(self, item_id: UUID):
        item = self.repository.get_project(item_id)
        if item is None:
            raise AppError("Project not found", code="ACCOUNTING_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)
        updated = self.repository.soft_delete_project(item)
        self.repository.db.commit()
        self.repository.db.refresh(updated)
        return updated
