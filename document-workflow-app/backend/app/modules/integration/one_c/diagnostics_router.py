from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.db.session import get_db
from app.modules.integration.log_repository import IntegrationLogRepository
from app.modules.integration.one_c.diagnostics_schemas import OneCDiagnosticsSettings, OneCTestConnectionResult
from app.modules.integration.one_c.diagnostics_service import OneCDiagnosticsService
from app.modules.integration.one_c.outbound_client import OneCOutboundClient
from app.modules.users.models import User

router = APIRouter(prefix="/integration/1c/diagnostics", tags=["integration-1c-diagnostics"])


def get_service(db: Session = Depends(get_db)) -> OneCDiagnosticsService:
    return OneCDiagnosticsService(IntegrationLogRepository(db), OneCOutboundClient())


@router.get("/settings", response_model=OneCDiagnosticsSettings)
def diagnostics_settings(
    _current_user: User = Depends(require_permission("integration_1c.diagnostics.read")),
    service: OneCDiagnosticsService = Depends(get_service),
):
    return service.get_settings()


@router.post("/test-connection", response_model=OneCTestConnectionResult)
def test_connection(
    current_user: User = Depends(require_permission("integration_1c.diagnostics.run")),
    service: OneCDiagnosticsService = Depends(get_service),
):
    return service.test_connection(current_user.id)
