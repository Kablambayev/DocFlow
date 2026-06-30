from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.db.session import get_db
from app.modules.cash_flow.bdds_report_repository import BddsReportRepository
from app.modules.cash_flow.bdds_report_schemas import (
    BddsReportByItemsResponse,
    BddsReportByOrganizationsResponse,
    BddsReportByPeriodsResponse,
    BddsReportByProjectsResponse,
    BddsReportDiagnosticsResponse,
    BddsReportSummaryResponse,
    DiagnosticType,
)
from app.modules.cash_flow.bdds_report_service import BddsReportService
from app.modules.users.models import User

router = APIRouter(prefix="/cash-flow/bdds-report", tags=["cash-flow-bdds-report"])


def get_service(db: Session = Depends(get_db)) -> BddsReportService:
    return BddsReportService(BddsReportRepository(db))


@router.get("/summary", response_model=BddsReportSummaryResponse)
def get_bdds_report_summary(
    date_from: date,
    date_to: date,
    organization_id: UUID | None = None,
    project_id: UUID | None = None,
    cash_flow_item_id: UUID | None = None,
    cash_flow_operation_type_id: UUID | None = None,
    currency_id: UUID | None = None,
    group_period: str | None = None,
    current_user: User = Depends(require_permission("cash_flow.report.read")),
    service: BddsReportService = Depends(get_service),
):
    return service.get_summary(
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
        project_id=project_id,
        cash_flow_item_id=cash_flow_item_id,
        cash_flow_operation_type_id=cash_flow_operation_type_id,
        currency_id=currency_id,
    )


@router.get("/by-items", response_model=BddsReportByItemsResponse)
def get_bdds_report_by_items(
    date_from: date,
    date_to: date,
    organization_id: UUID | None = None,
    project_id: UUID | None = None,
    cash_flow_item_id: UUID | None = None,
    cash_flow_operation_type_id: UUID | None = None,
    currency_id: UUID | None = None,
    group_period: str | None = None,
    current_user: User = Depends(require_permission("cash_flow.report.read")),
    service: BddsReportService = Depends(get_service),
):
    return service.get_by_items(
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
        project_id=project_id,
        cash_flow_item_id=cash_flow_item_id,
        cash_flow_operation_type_id=cash_flow_operation_type_id,
        currency_id=currency_id,
    )


@router.get("/by-projects", response_model=BddsReportByProjectsResponse)
def get_bdds_report_by_projects(
    date_from: date,
    date_to: date,
    organization_id: UUID | None = None,
    project_id: UUID | None = None,
    cash_flow_item_id: UUID | None = None,
    cash_flow_operation_type_id: UUID | None = None,
    currency_id: UUID | None = None,
    group_period: str | None = None,
    current_user: User = Depends(require_permission("cash_flow.report.read")),
    service: BddsReportService = Depends(get_service),
):
    return service.get_by_projects(
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
        project_id=project_id,
        cash_flow_item_id=cash_flow_item_id,
        cash_flow_operation_type_id=cash_flow_operation_type_id,
        currency_id=currency_id,
    )


@router.get("/by-organizations", response_model=BddsReportByOrganizationsResponse)
def get_bdds_report_by_organizations(
    date_from: date,
    date_to: date,
    organization_id: UUID | None = None,
    project_id: UUID | None = None,
    cash_flow_item_id: UUID | None = None,
    cash_flow_operation_type_id: UUID | None = None,
    currency_id: UUID | None = None,
    group_period: str | None = None,
    current_user: User = Depends(require_permission("cash_flow.report.read")),
    service: BddsReportService = Depends(get_service),
):
    return service.get_by_organizations(
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
        project_id=project_id,
        cash_flow_item_id=cash_flow_item_id,
        cash_flow_operation_type_id=cash_flow_operation_type_id,
        currency_id=currency_id,
    )


@router.get("/by-periods", response_model=BddsReportByPeriodsResponse)
def get_bdds_report_by_periods(
    date_from: date,
    date_to: date,
    organization_id: UUID | None = None,
    project_id: UUID | None = None,
    cash_flow_item_id: UUID | None = None,
    cash_flow_operation_type_id: UUID | None = None,
    currency_id: UUID | None = None,
    group_period: str | None = Query(default="month"),
    current_user: User = Depends(require_permission("cash_flow.report.read")),
    service: BddsReportService = Depends(get_service),
):
    return service.get_by_periods(
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
        project_id=project_id,
        cash_flow_item_id=cash_flow_item_id,
        cash_flow_operation_type_id=cash_flow_operation_type_id,
        currency_id=currency_id,
        group_period=group_period,
    )


@router.get("/diagnostics", response_model=BddsReportDiagnosticsResponse)
def get_bdds_report_diagnostics(
    date_from: date,
    date_to: date,
    organization_id: UUID | None = None,
    project_id: UUID | None = None,
    cash_flow_item_id: UUID | None = None,
    cash_flow_operation_type_id: UUID | None = None,
    currency_id: UUID | None = None,
    group_period: str | None = None,
    diagnostic_type: DiagnosticType | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("cash_flow.report.read")),
    service: BddsReportService = Depends(get_service),
):
    return service.get_diagnostics(
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        organization_id=organization_id,
        project_id=project_id,
        currency_id=currency_id,
        diagnostic_type=diagnostic_type,
        limit=limit,
        offset=offset,
    )
