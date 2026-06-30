from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_permission
from app.db.session import get_db
from app.modules.cash_flow.allocation_repository import CashFlowAllocationRepository
from app.modules.cash_flow.allocation_schemas import (
    CashFlowAllocationActionResponse,
    CashFlowAllocationDetailRead,
    CashFlowAllocationMetricsResponse,
    CashFlowAllocationUpdateRequest,
    CashFlowAllocationsResponse,
)
from app.modules.cash_flow.allocation_service import CashFlowAllocationService
from app.modules.users.models import User

router = APIRouter(prefix="/cash-flow/allocations", tags=["cash-flow-allocations"])


def get_service(db: Session = Depends(get_db)) -> CashFlowAllocationService:
    return CashFlowAllocationService(CashFlowAllocationRepository(db))


@router.get("", response_model=CashFlowAllocationsResponse)
def get_cash_flow_allocations(
    allocation_status: str | None = None,
    cash_flow_direction: Literal["Inflow", "Outflow"] | None = None,
    organization_id: UUID | None = None,
    counterparty_id: UUID | None = None,
    project_id: UUID | None = None,
    cash_flow_item_id: UUID | None = None,
    currency_id: UUID | None = None,
    source_changed: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("cash_flow.allocation.read")),
    service: CashFlowAllocationService = Depends(get_service),
):
    return service.list_allocations(
        current_user=current_user,
        allocation_status=allocation_status,
        cash_flow_direction=cash_flow_direction,
        organization_id=organization_id,
        counterparty_id=counterparty_id,
        project_id=project_id,
        cash_flow_item_id=cash_flow_item_id,
        currency_id=currency_id,
        source_changed=source_changed,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/metrics", response_model=CashFlowAllocationMetricsResponse)
def get_cash_flow_allocation_metrics(
    current_user: User = Depends(require_permission("cash_flow.allocation.read")),
    service: CashFlowAllocationService = Depends(get_service),
):
    return service.get_metrics(current_user)


@router.get("/{document_id}", response_model=CashFlowAllocationDetailRead)
def get_cash_flow_allocation(
    document_id: UUID,
    current_user: User = Depends(require_permission("cash_flow.allocation.read")),
    service: CashFlowAllocationService = Depends(get_service),
):
    return service.get_detail(document_id, current_user)


@router.put("/{document_id}", response_model=CashFlowAllocationDetailRead)
def update_cash_flow_allocation(
    document_id: UUID,
    payload: CashFlowAllocationUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: CashFlowAllocationService = Depends(get_service),
):
    return service.update_allocation(document_id, payload, current_user)


@router.post("/{document_id}/complete", response_model=CashFlowAllocationActionResponse)
def complete_cash_flow_allocation(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CashFlowAllocationService = Depends(get_service),
):
    return service.complete(document_id, current_user)


@router.post("/{document_id}/ignore", response_model=CashFlowAllocationActionResponse)
def ignore_cash_flow_allocation(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CashFlowAllocationService = Depends(get_service),
):
    return service.ignore(document_id, current_user)


@router.post("/{document_id}/reopen", response_model=CashFlowAllocationActionResponse)
def reopen_cash_flow_allocation(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CashFlowAllocationService = Depends(get_service),
):
    return service.reopen(document_id, current_user)
