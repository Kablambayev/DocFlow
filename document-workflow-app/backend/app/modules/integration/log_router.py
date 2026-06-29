from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.integration.log_repository import IntegrationLogRepository
from app.modules.integration.log_schemas import IntegrationLogDetail, IntegrationLogsResponse
from app.modules.integration.log_service import IntegrationLogService
from app.modules.integration.one_c.outbound_client import OneCOutboundClient
from app.modules.integration.one_c.outbound_service import OneCOutboundService
from app.modules.integration.one_c.payment_export_repository import PaymentRequest1CExportRepository
from app.modules.users.models import User

router = APIRouter(prefix="/integration/logs", tags=["integration-logs"])


def get_log_service(db: Session = Depends(get_db)) -> IntegrationLogService:
    return IntegrationLogService(IntegrationLogRepository(db))


def get_outbound_service(db: Session = Depends(get_db)) -> OneCOutboundService:
    return OneCOutboundService(PaymentRequest1CExportRepository(db), OneCOutboundClient())


@router.get("", response_model=IntegrationLogsResponse)
def list_integration_logs(
    direction: Literal["Inbound", "Outbound"] | None = None,
    operation_type: str | None = None,
    status: str | None = None,
    document_id: UUID | None = None,
    date_from: datetime | date | None = None,
    date_to: datetime | date | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["created_at", "duration_ms", "status", "operation_type"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(get_current_user),
    service: IntegrationLogService = Depends(get_log_service),
):
    return service.get_logs(
        current_user_id=current_user.id,
        direction=direction,
        operation_type=operation_type,
        status=status,
        document_id=document_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{log_id}", response_model=IntegrationLogDetail)
def get_integration_log_detail(
    log_id: UUID,
    current_user: User = Depends(get_current_user),
    service: IntegrationLogService = Depends(get_log_service),
):
    return service.get_log_by_id(log_id, current_user.id)


@router.post("/{log_id}/retry")
def retry_integration_log(
    log_id: UUID,
    current_user: User = Depends(get_current_user),
    log_service: IntegrationLogService = Depends(get_log_service),
    outbound_service: OneCOutboundService = Depends(get_outbound_service),
):
    log = log_service.ensure_retry_supported(log_id)
    return outbound_service.send_approved_payment_request_to_1c(log.document_id, current_user, force=True)
