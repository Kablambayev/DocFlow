from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.db.session import get_db
from app.modules.treasury.repository import TreasuryRepository
from app.modules.treasury.schemas import TreasuryMetricsResponse, TreasuryPaymentRequestsResponse
from app.modules.treasury.service import TreasuryService
from app.modules.users.models import User

router = APIRouter(prefix="/treasury", tags=["treasury"])


def get_service(db: Session = Depends(get_db)) -> TreasuryService:
    return TreasuryService(TreasuryRepository(db))


@router.get("/payment-requests", response_model=TreasuryPaymentRequestsResponse)
def get_treasury_payment_requests(
    export_status: Literal["not_exported", "Pending", "Sent", "CreatedIn1C", "AlreadyExistsIn1C", "Failed"] | None = None,
    approval_status: str = "Approved",
    organization_id: UUID | None = None,
    counterparty_id: UUID | None = None,
    project_id: UUID | None = None,
    currency_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    amount_from: Decimal | None = None,
    amount_to: Decimal | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["approved_at", "document_date", "amount", "number"] = "approved_at",
    sort_order: Literal["asc", "desc"] = "desc",
    _: User = Depends(require_permission("treasury.payment_request.read")),
    service: TreasuryService = Depends(get_service),
):
    return service.list_payment_requests(
        export_status=export_status,
        approval_status=approval_status,
        organization_id=organization_id,
        counterparty_id=counterparty_id,
        project_id=project_id,
        currency_id=currency_id,
        date_from=date_from,
        date_to=date_to,
        amount_from=amount_from,
        amount_to=amount_to,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/payment-requests/metrics", response_model=TreasuryMetricsResponse)
def get_treasury_payment_request_metrics(
    _: User = Depends(require_permission("treasury.payment_request.read")),
    service: TreasuryService = Depends(get_service),
):
    return service.get_metrics()
