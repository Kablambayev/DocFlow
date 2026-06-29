from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.accounting.models import (
    AccountingCashFlowItem,
    AccountingCashFlowOperationType,
    AccountingCounterparty,
    AccountingCounterpartyContract,
    AccountingCurrency,
    AccountingExpenseItem,
    AccountingOrganization,
    AccountingProject,
)
from app.modules.accounting.schemas import (
    AccountingCashFlowItemCreate,
    AccountingCashFlowItemUpdate,
    AccountingProjectCreate,
    AccountingProjectUpdate,
    CashFlowOperationTypeCreate,
    CashFlowOperationTypeUpdate,
)


def _search_filter(search: str | None, *columns):
    if not search:
        return None
    pattern = f"%{search.strip()}%"
    predicates = [column.ilike(pattern) for column in columns]
    return or_(*predicates)


class AccountingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_organizations(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        stmt: Select[tuple[AccountingOrganization]] = select(AccountingOrganization)
        predicate = _search_filter(search, AccountingOrganization.code, AccountingOrganization.name, AccountingOrganization.full_name)
        if predicate is not None:
            stmt = stmt.where(predicate)
        if is_active is not None:
            stmt = stmt.where(AccountingOrganization.is_active.is_(is_active))
        stmt = stmt.order_by(AccountingOrganization.name).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def list_counterparties(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        stmt: Select[tuple[AccountingCounterparty]] = select(AccountingCounterparty)
        predicate = _search_filter(
            search,
            AccountingCounterparty.code,
            AccountingCounterparty.name,
            AccountingCounterparty.full_name,
            AccountingCounterparty.bin_iin,
        )
        if predicate is not None:
            stmt = stmt.where(predicate)
        if is_active is not None:
            stmt = stmt.where(AccountingCounterparty.is_active.is_(is_active))
        stmt = stmt.order_by(AccountingCounterparty.name).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def list_counterparty_contracts(
        self,
        organization_id: UUID | None,
        counterparty_id: UUID | None,
        search: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ):
        stmt: Select[tuple[AccountingCounterpartyContract]] = select(AccountingCounterpartyContract)
        if organization_id is not None:
            stmt = stmt.where(AccountingCounterpartyContract.organization_id == organization_id)
        if counterparty_id is not None:
            stmt = stmt.where(AccountingCounterpartyContract.counterparty_id == counterparty_id)
        predicate = _search_filter(
            search,
            AccountingCounterpartyContract.code,
            AccountingCounterpartyContract.name,
            AccountingCounterpartyContract.number,
        )
        if predicate is not None:
            stmt = stmt.where(predicate)
        if is_active is not None:
            stmt = stmt.where(AccountingCounterpartyContract.is_active.is_(is_active))
        stmt = stmt.order_by(AccountingCounterpartyContract.name).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def list_currencies(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        stmt: Select[tuple[AccountingCurrency]] = select(AccountingCurrency)
        predicate = _search_filter(search, AccountingCurrency.code, AccountingCurrency.name, AccountingCurrency.full_name)
        if predicate is not None:
            stmt = stmt.where(predicate)
        if is_active is not None:
            stmt = stmt.where(AccountingCurrency.is_active.is_(is_active))
        stmt = stmt.order_by(AccountingCurrency.code).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def list_expense_items(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        stmt: Select[tuple[AccountingExpenseItem]] = select(AccountingExpenseItem)
        predicate = _search_filter(search, AccountingExpenseItem.code, AccountingExpenseItem.name, AccountingExpenseItem.full_name)
        if predicate is not None:
            stmt = stmt.where(predicate)
        if is_active is not None:
            stmt = stmt.where(AccountingExpenseItem.is_active.is_(is_active))
        stmt = stmt.order_by(AccountingExpenseItem.name).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def list_cash_flow_items(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        stmt: Select[tuple[AccountingCashFlowItem]] = select(AccountingCashFlowItem)
        predicate = _search_filter(search, AccountingCashFlowItem.code, AccountingCashFlowItem.name, AccountingCashFlowItem.full_name)
        if predicate is not None:
            stmt = stmt.where(predicate)
        if is_active is not None:
            stmt = stmt.where(AccountingCashFlowItem.is_active.is_(is_active))
        stmt = stmt.order_by(AccountingCashFlowItem.name).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def get_cash_flow_item(self, item_id: UUID):
        return self.db.get(AccountingCashFlowItem, item_id)

    def get_cash_flow_item_by_external_id(self, source_system: str, external_id: str):
        return self.db.scalar(
            select(AccountingCashFlowItem).where(
                AccountingCashFlowItem.source_system == source_system,
                AccountingCashFlowItem.external_id == external_id,
            )
        )

    def get_cash_flow_item_by_code(self, code: str):
        return self.db.scalar(select(AccountingCashFlowItem).where(func.lower(AccountingCashFlowItem.code) == code.lower()))

    def get_cash_flow_item_by_name(self, name: str):
        return self.db.scalar(select(AccountingCashFlowItem).where(func.lower(AccountingCashFlowItem.name) == name.lower()))

    def create_cash_flow_item(self, payload: AccountingCashFlowItemCreate):
        item = AccountingCashFlowItem(**payload.model_dump())
        self.db.add(item)
        self.db.flush()
        return item

    def update_cash_flow_item(self, item: AccountingCashFlowItem, payload: AccountingCashFlowItemUpdate):
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        self.db.flush()
        return item

    def list_cash_flow_operation_types(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        stmt: Select[tuple[AccountingCashFlowOperationType]] = select(AccountingCashFlowOperationType)
        predicate = _search_filter(search, AccountingCashFlowOperationType.code, AccountingCashFlowOperationType.name)
        if predicate is not None:
            stmt = stmt.where(predicate)
        if is_active is not None:
            stmt = stmt.where(AccountingCashFlowOperationType.is_active.is_(is_active))
        stmt = stmt.order_by(AccountingCashFlowOperationType.sort_order, AccountingCashFlowOperationType.name).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def get_cash_flow_operation_type_by_code(self, code: str):
        return self.db.scalar(select(AccountingCashFlowOperationType).where(func.lower(AccountingCashFlowOperationType.code) == code.lower()))

    def get_cash_flow_operation_type(self, item_id: UUID):
        return self.db.get(AccountingCashFlowOperationType, item_id)

    def create_cash_flow_operation_type(self, payload: CashFlowOperationTypeCreate):
        item = AccountingCashFlowOperationType(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            sort_order=payload.sort_order,
            is_active=True,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update_cash_flow_operation_type(self, item: AccountingCashFlowOperationType, payload: CashFlowOperationTypeUpdate):
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        self.db.flush()
        return item

    def soft_delete_cash_flow_operation_type(self, item: AccountingCashFlowOperationType):
        item.is_active = False
        self.db.flush()
        return item

    def list_projects(self, search: str | None, is_active: bool | None, limit: int, offset: int):
        stmt: Select[tuple[AccountingProject]] = select(AccountingProject)
        predicate = _search_filter(search, AccountingProject.code, AccountingProject.name)
        if predicate is not None:
            stmt = stmt.where(predicate)
        if is_active is not None:
            stmt = stmt.where(AccountingProject.is_active.is_(is_active))
        stmt = stmt.order_by(AccountingProject.code).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def get_project_by_code(self, code: str):
        return self.db.scalar(select(AccountingProject).where(func.lower(AccountingProject.code) == code.lower()))

    def get_project(self, item_id: UUID):
        return self.db.get(AccountingProject, item_id)

    def create_project(self, payload: AccountingProjectCreate):
        item = AccountingProject(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            start_date=payload.start_date,
            end_date=payload.end_date,
            responsible_user_id=payload.responsible_user_id,
            is_active=True,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update_project(self, item: AccountingProject, payload: AccountingProjectUpdate):
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        self.db.flush()
        return item

    def soft_delete_project(self, item: AccountingProject):
        item.is_active = False
        self.db.flush()
        return item

    def get_active_organization(self, item_id: UUID):
        return self.db.scalar(select(AccountingOrganization).where(AccountingOrganization.id == item_id, AccountingOrganization.is_active.is_(True)))

    def get_active_counterparty(self, item_id: UUID):
        return self.db.scalar(select(AccountingCounterparty).where(AccountingCounterparty.id == item_id, AccountingCounterparty.is_active.is_(True)))

    def get_active_contract(self, item_id: UUID):
        return self.db.scalar(select(AccountingCounterpartyContract).where(AccountingCounterpartyContract.id == item_id, AccountingCounterpartyContract.is_active.is_(True)))

    def get_active_currency(self, item_id: UUID):
        return self.db.scalar(select(AccountingCurrency).where(AccountingCurrency.id == item_id, AccountingCurrency.is_active.is_(True)))

    def get_active_expense_item(self, item_id: UUID):
        return self.db.scalar(select(AccountingExpenseItem).where(AccountingExpenseItem.id == item_id, AccountingExpenseItem.is_active.is_(True)))

    def get_active_cash_flow_item(self, item_id: UUID):
        return self.db.scalar(select(AccountingCashFlowItem).where(AccountingCashFlowItem.id == item_id, AccountingCashFlowItem.is_active.is_(True)))

    def get_active_cash_flow_operation_type(self, item_id: UUID):
        return self.db.scalar(select(AccountingCashFlowOperationType).where(AccountingCashFlowOperationType.id == item_id, AccountingCashFlowOperationType.is_active.is_(True)))

    def get_active_project(self, item_id: UUID):
        return self.db.scalar(select(AccountingProject).where(AccountingProject.id == item_id, AccountingProject.is_active.is_(True)))
