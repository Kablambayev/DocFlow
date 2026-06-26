from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.db.session import get_db
from app.modules.integration.one_c.inbound_service import OneCInboundService
from app.modules.integration.one_c.schemas import ImportEnvelope, ImportResult
from app.modules.users.models import User

router = APIRouter(prefix="/integration/1c", tags=["integration-1c"])


def get_service(db: Session = Depends(get_db)) -> OneCInboundService:
    return OneCInboundService(db)


@router.post(
    "/organizations/import",
    response_model=ImportResult,
    summary="Import organizations from 1C",
)
def import_organizations(
    payload: ImportEnvelope,
    current_user: User = Depends(require_permission("accounting.sync")),
    service: OneCInboundService = Depends(get_service),
):
    return service.import_organizations(payload, current_user.id)


@router.post(
    "/counterparties/import",
    response_model=ImportResult,
    summary="Import counterparties from 1C",
)
def import_counterparties(
    payload: ImportEnvelope,
    current_user: User = Depends(require_permission("accounting.sync")),
    service: OneCInboundService = Depends(get_service),
):
    return service.import_counterparties(payload, current_user.id)


@router.post(
    "/currencies/import",
    response_model=ImportResult,
    summary="Import currencies from 1C",
)
def import_currencies(
    payload: ImportEnvelope,
    current_user: User = Depends(require_permission("accounting.sync")),
    service: OneCInboundService = Depends(get_service),
):
    return service.import_currencies(payload, current_user.id)


@router.post(
    "/expense-items/import",
    response_model=ImportResult,
    summary="Import expense items from 1C",
)
def import_expense_items(
    payload: ImportEnvelope,
    current_user: User = Depends(require_permission("accounting.sync")),
    service: OneCInboundService = Depends(get_service),
):
    return service.import_expense_items(payload, current_user.id)


@router.post(
    "/counterparty-contracts/import",
    response_model=ImportResult,
    summary="Import counterparty contracts from 1C",
)
def import_counterparty_contracts(
    payload: ImportEnvelope,
    current_user: User = Depends(require_permission("accounting.sync")),
    service: OneCInboundService = Depends(get_service),
):
    return service.import_counterparty_contracts(payload, current_user.id)
