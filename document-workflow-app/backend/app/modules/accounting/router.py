from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.db.session import get_db
from app.modules.accounting.repository import AccountingRepository
from app.modules.accounting.schemas import (
    AccountingCounterpartyContractRead,
    AccountingCounterpartyRead,
    AccountingCurrencyRead,
    AccountingExpenseItemRead,
    AccountingOrganizationRead,
    AccountingProjectCreate,
    AccountingProjectRead,
    AccountingProjectUpdate,
    CashFlowOperationTypeCreate,
    CashFlowOperationTypeRead,
    CashFlowOperationTypeUpdate,
)
from app.modules.accounting.service import AccountingService
from app.modules.users.models import User

router = APIRouter(prefix="/accounting", tags=["accounting"])


def get_service(db: Session = Depends(get_db)) -> AccountingService:
    return AccountingService(AccountingRepository(db))


@router.get("/organizations", response_model=list[AccountingOrganizationRead])
def list_organizations(
    search: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_permission("accounting.read")),
    service: AccountingService = Depends(get_service),
):
    return service.list_organizations(search, is_active, limit, offset)


@router.get("/counterparties", response_model=list[AccountingCounterpartyRead])
def list_counterparties(
    search: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_permission("accounting.read")),
    service: AccountingService = Depends(get_service),
):
    return service.list_counterparties(search, is_active, limit, offset)


@router.get("/counterparty-contracts", response_model=list[AccountingCounterpartyContractRead])
def list_counterparty_contracts(
    organization_id: UUID | None = None,
    counterparty_id: UUID | None = None,
    search: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_permission("accounting.read")),
    service: AccountingService = Depends(get_service),
):
    return service.list_counterparty_contracts(organization_id, counterparty_id, search, is_active, limit, offset)


@router.get("/currencies", response_model=list[AccountingCurrencyRead])
def list_currencies(
    search: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_permission("accounting.read")),
    service: AccountingService = Depends(get_service),
):
    return service.list_currencies(search, is_active, limit, offset)


@router.get("/expense-items", response_model=list[AccountingExpenseItemRead])
def list_expense_items(
    search: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_permission("accounting.read")),
    service: AccountingService = Depends(get_service),
):
    return service.list_expense_items(search, is_active, limit, offset)


@router.get("/cash-flow-operation-types", response_model=list[CashFlowOperationTypeRead])
def list_cash_flow_operation_types(
    search: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_permission("accounting.read")),
    service: AccountingService = Depends(get_service),
):
    return service.list_cash_flow_operation_types(search, is_active, limit, offset)


@router.post("/cash-flow-operation-types", response_model=CashFlowOperationTypeRead)
def create_cash_flow_operation_type(
    payload: CashFlowOperationTypeCreate,
    _: User = Depends(require_permission("accounting.manage")),
    service: AccountingService = Depends(get_service),
):
    return service.create_cash_flow_operation_type(payload)


@router.put("/cash-flow-operation-types/{id}", response_model=CashFlowOperationTypeRead)
def update_cash_flow_operation_type(
    id: UUID,
    payload: CashFlowOperationTypeUpdate,
    _: User = Depends(require_permission("accounting.manage")),
    service: AccountingService = Depends(get_service),
):
    return service.update_cash_flow_operation_type(id, payload)


@router.delete("/cash-flow-operation-types/{id}", response_model=CashFlowOperationTypeRead)
def delete_cash_flow_operation_type(
    id: UUID,
    _: User = Depends(require_permission("accounting.manage")),
    service: AccountingService = Depends(get_service),
):
    return service.soft_delete_cash_flow_operation_type(id)


@router.get("/projects", response_model=list[AccountingProjectRead])
def list_projects(
    search: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_permission("accounting.read")),
    service: AccountingService = Depends(get_service),
):
    return service.list_projects(search, is_active, limit, offset)


@router.post("/projects", response_model=AccountingProjectRead)
def create_project(
    payload: AccountingProjectCreate,
    _: User = Depends(require_permission("accounting.manage")),
    service: AccountingService = Depends(get_service),
):
    return service.create_project(payload)


@router.put("/projects/{id}", response_model=AccountingProjectRead)
def update_project(
    id: UUID,
    payload: AccountingProjectUpdate,
    _: User = Depends(require_permission("accounting.manage")),
    service: AccountingService = Depends(get_service),
):
    return service.update_project(id, payload)


@router.delete("/projects/{id}", response_model=AccountingProjectRead)
def delete_project(
    id: UUID,
    _: User = Depends(require_permission("accounting.manage")),
    service: AccountingService = Depends(get_service),
):
    return service.soft_delete_project(id)
