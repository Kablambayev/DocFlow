from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


GroupPeriod = Literal["day", "week", "month", "quarter", "year"]


class BddsReportLookup(BaseModel):
    id: UUID
    code: str | None = None
    name: str
    direction: str | None = None


class BddsReportCurrency(BaseModel):
    id: UUID
    code: str
    name: str | None = None


class BddsReportTotalsByCurrencyItem(BaseModel):
    currency: BddsReportCurrency | None = None
    inflow_total: Decimal
    outflow_total: Decimal
    net_cash_flow: Decimal


class BddsReportSummaryDiagnostics(BaseModel):
    ignored_allocations_count: int
    invalid_allocations_count: int
    needs_enrichment_count: int


class BddsReportSummaryResponse(BaseModel):
    date_from: date
    date_to: date
    currency: BddsReportCurrency | None = None
    inflow_total: Decimal | None = None
    outflow_total: Decimal | None = None
    net_cash_flow: Decimal | None = None
    allocations_count: int
    inflow_count: int
    outflow_count: int
    diagnostics: BddsReportSummaryDiagnostics
    totals_by_currency: list[BddsReportTotalsByCurrencyItem] = []


class BddsReportByItemRow(BaseModel):
    cash_flow_item: BddsReportLookup
    currency: BddsReportCurrency | None = None
    inflow_total: Decimal
    outflow_total: Decimal
    net_cash_flow: Decimal
    allocations_count: int


class BddsReportByItemsResponse(BaseModel):
    items: list[BddsReportByItemRow]
    total: int


class BddsReportByProjectRow(BaseModel):
    project: BddsReportLookup | None = None
    project_name: str
    currency: BddsReportCurrency | None = None
    inflow_total: Decimal
    outflow_total: Decimal
    net_cash_flow: Decimal
    allocations_count: int


class BddsReportByProjectsResponse(BaseModel):
    items: list[BddsReportByProjectRow]
    total: int


class BddsReportByOrganizationRow(BaseModel):
    organization: BddsReportLookup
    currency: BddsReportCurrency | None = None
    inflow_total: Decimal
    outflow_total: Decimal
    net_cash_flow: Decimal
    allocations_count: int


class BddsReportByOrganizationsResponse(BaseModel):
    items: list[BddsReportByOrganizationRow]
    total: int


class BddsReportByPeriodRow(BaseModel):
    period_start: date
    period_end: date
    currency: BddsReportCurrency | None = None
    inflow_total: Decimal
    outflow_total: Decimal
    net_cash_flow: Decimal
    allocations_count: int


class BddsReportByPeriodsResponse(BaseModel):
    group_period: GroupPeriod
    items: list[BddsReportByPeriodRow]
    total: int


DiagnosticType = Literal[
    "needs_enrichment",
    "ignored",
    "missing_direction",
    "missing_date",
    "missing_amount",
    "missing_cash_flow_item",
    "missing_currency",
    "source_changed",
]


class BddsReportDiagnosticRow(BaseModel):
    document_id: UUID
    source_document_number: str | None = None
    source_document_date: date | None = None
    source_document_type_1c: str | None = None
    diagnostic_type: DiagnosticType
    allocation_status: str
    message: str


class BddsReportDiagnosticsResponse(BaseModel):
    items: list[BddsReportDiagnosticRow]
    total: int
    limit: int
    offset: int
