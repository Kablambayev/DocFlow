from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.integration.one_c.outbound_client import OneCOutboundClient
from app.modules.integration.one_c.outbound_service import OneCOutboundService
from app.modules.integration.one_c.payment_export_repository import PaymentRequest1CExportRepository
from app.modules.integration.one_c.payment_export_schemas import (
    PaymentRequest1CAlreadyExportedResponse,
    PaymentRequest1CExportNotExportedResponse,
    PaymentRequest1CExportRead,
    PaymentRequest1CSendResponse,
)
from app.modules.users.models import User

router = APIRouter(prefix="/integration/1c", tags=["integration-1c"])


def get_service(db: Session = Depends(get_db)) -> OneCOutboundService:
    return OneCOutboundService(PaymentRequest1CExportRepository(db), OneCOutboundClient())


@router.post(
    "/payment-requests/{document_id}/send",
    response_model=PaymentRequest1CSendResponse | PaymentRequest1CAlreadyExportedResponse,
    summary="Send approved payment request to 1C",
)
def send_payment_request_to_1c(
    document_id: UUID,
    force: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    service: OneCOutboundService = Depends(get_service),
):
    return service.send_approved_payment_request_to_1c(document_id, current_user, force)


@router.get(
    "/payment-requests/{document_id}/export",
    response_model=PaymentRequest1CExportRead | PaymentRequest1CExportNotExportedResponse,
    summary="Get payment request export status",
)
def get_payment_request_export(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    service: OneCOutboundService = Depends(get_service),
):
    return service.get_export(document_id, current_user)