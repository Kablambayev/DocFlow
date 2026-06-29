from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_permission
from app.db.session import get_db
from app.modules.payment_registers.repository import PaymentRegisterRepository
from app.modules.payment_registers.schemas import (
    PaymentRegisterActionResponse,
    PaymentRegisterAvailableRequestsResponse,
    PaymentRegisterCreate,
    PaymentRegisterDetailRead,
    PaymentRegisterRowsAddRequest,
    PaymentRegisterRowsAddResponse,
    PaymentRegisterSendResponse,
    PaymentRegisterUpdate,
    PaymentRegistersResponse,
)
from app.modules.payment_registers.service import PaymentRegisterService
from app.modules.users.models import User

router = APIRouter(prefix="/payment-registers", tags=["payment-registers"])


def get_service(db: Session = Depends(get_db)) -> PaymentRegisterService:
    return PaymentRegisterService(PaymentRegisterRepository(db))


@router.get("", response_model=PaymentRegistersResponse)
def get_payment_registers(
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    organization_id: UUID | None = None,
    currency_id: UUID | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["number", "date", "status", "total_amount", "created_at", "sent_at"] = "date",
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(require_permission("payment_register.read")),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.list_registers(
        current_user=current_user,
        status=status,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
        currency_id=currency_id,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("", response_model=PaymentRegisterDetailRead)
def create_payment_register(
    payload: PaymentRegisterCreate,
    current_user: User = Depends(get_current_user),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.create_register(payload, current_user)


@router.get("/available-payment-requests", response_model=PaymentRegisterAvailableRequestsResponse)
def get_available_payment_requests(
    organization_id: UUID | None = None,
    currency_id: UUID | None = None,
    search: str | None = None,
    include_failed_exports: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("payment_register.read")),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.list_available_payment_requests(
        current_user=current_user,
        organization_id=organization_id,
        currency_id=currency_id,
        search=search,
        include_failed_exports=include_failed_exports,
        limit=limit,
        offset=offset,
    )


@router.get("/{register_id}", response_model=PaymentRegisterDetailRead)
def get_payment_register(
    register_id: UUID,
    current_user: User = Depends(require_permission("payment_register.read")),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.get_register(register_id, current_user)


@router.put("/{register_id}", response_model=PaymentRegisterDetailRead)
def update_payment_register(
    register_id: UUID,
    payload: PaymentRegisterUpdate,
    current_user: User = Depends(get_current_user),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.update_register(register_id, payload, current_user)


@router.delete("/{register_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_register(
    register_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentRegisterService = Depends(get_service),
):
    service.delete_register(register_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{register_id}/rows", response_model=PaymentRegisterRowsAddResponse)
def add_payment_register_rows(
    register_id: UUID,
    payload: PaymentRegisterRowsAddRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.add_rows(register_id, payload, current_user)


@router.delete("/{register_id}/rows/{row_id}", response_model=PaymentRegisterDetailRead)
def delete_payment_register_row(
    register_id: UUID,
    row_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.remove_row(register_id, row_id, current_user)


@router.post("/{register_id}/mark-ready", response_model=PaymentRegisterActionResponse)
def mark_payment_register_ready(
    register_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.mark_ready(register_id, current_user)


@router.post("/{register_id}/send-to-1c", response_model=PaymentRegisterSendResponse)
def send_payment_register_to_1c(
    register_id: UUID,
    force: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.send_to_1c(register_id, current_user, force=force)


@router.post("/{register_id}/cancel", response_model=PaymentRegisterActionResponse)
def cancel_payment_register(
    register_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PaymentRegisterService = Depends(get_service),
):
    return service.cancel(register_id, current_user)
