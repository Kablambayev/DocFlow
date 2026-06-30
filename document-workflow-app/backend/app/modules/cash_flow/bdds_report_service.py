from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Iterable
from uuid import UUID

from fastapi import status

from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.cash_flow.bdds_report_repository import BddsReportRepository
from app.modules.cash_flow.bdds_report_schemas import (
    BddsReportByItemRow,
    BddsReportByItemsResponse,
    BddsReportByOrganizationRow,
    BddsReportByOrganizationsResponse,
    BddsReportByPeriodRow,
    BddsReportByPeriodsResponse,
    BddsReportByProjectRow,
    BddsReportByProjectsResponse,
    BddsReportCurrency,
    BddsReportDiagnosticRow,
    BddsReportDiagnosticsResponse,
    BddsReportLookup,
    BddsReportSummaryDiagnostics,
    BddsReportSummaryResponse,
    BddsReportTotalsByCurrencyItem,
    DiagnosticType,
    GroupPeriod,
)

ZERO = Decimal("0")
VALID_GROUP_PERIODS = {"day", "week", "month", "quarter", "year"}
DIAGNOSTIC_MESSAGES: dict[DiagnosticType, str] = {
    "needs_enrichment": "Allocation requires enrichment before it can be included in BDDS report",
    "ignored": "Allocation is ignored and excluded from BDDS report",
    "missing_direction": "Allocation has no valid cash flow direction and is excluded from BDDS report",
    "missing_date": "Allocation has no source document date and is excluded from BDDS report",
    "missing_amount": "Allocation has no valid non-zero amount and is excluded from BDDS report",
    "missing_cash_flow_item": "Allocation has no cash flow item and is excluded from BDDS report",
    "missing_currency": "Allocation has no currency and is excluded from BDDS report",
    "source_changed": "Source document changed after allocation was completed or ignored",
}


@dataclass
class _Lookup:
    id: UUID
    code: str | None
    name: str
    direction: str | None = None


@dataclass
class _Currency:
    id: UUID
    code: str
    name: str | None


@dataclass
class _NormalizedAllocation:
    document_id: UUID
    allocation_status: str
    source_document_number: str | None
    source_document_type_1c: str | None
    source_document_date: date | None
    cash_flow_direction: str | None
    organization: _Lookup | None
    project: _Lookup | None
    cash_flow_item: _Lookup | None
    cash_flow_operation_type: _Lookup | None
    currency: _Currency | None
    amount: Decimal | None
    source_changed: bool
    diagnostic_types: list[DiagnosticType]
    included_in_report: bool


@dataclass
class _Totals:
    inflow_total: Decimal = ZERO
    outflow_total: Decimal = ZERO
    inflow_count: int = 0
    outflow_count: int = 0
    allocations_count: int = 0

    @property
    def net_cash_flow(self) -> Decimal:
        return self.inflow_total - self.outflow_total


class BddsReportService:
    def __init__(self, repository: BddsReportRepository):
        self.repository = repository

    def get_summary(
        self,
        *,
        current_user,
        date_from: date,
        date_to: date,
        organization_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        cash_flow_operation_type_id: UUID | None,
        currency_id: UUID | None,
    ) -> BddsReportSummaryResponse:
        self._require_permission(current_user.id, "cash_flow.report.read")
        self._validate_period(date_from, date_to)

        records = self._filtered_records(
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id,
            project_id=project_id,
            cash_flow_item_id=cash_flow_item_id,
            cash_flow_operation_type_id=cash_flow_operation_type_id,
            currency_id=currency_id,
        )
        included = [record for record in records if record.included_in_report]
        totals_by_currency = self._totals_by_currency(included)
        diagnostics = BddsReportSummaryDiagnostics(
            ignored_allocations_count=sum(1 for record in records if record.allocation_status == "Ignored"),
            invalid_allocations_count=sum(
                1 for record in records if record.allocation_status == "Completed" and not record.included_in_report
            ),
            needs_enrichment_count=sum(1 for record in records if record.allocation_status == "NeedsEnrichment"),
        )

        if currency_id is not None:
            total = self._aggregate_totals(included)
            currency = included[0].currency if included else self._lookup_currency(currency_id)
            return BddsReportSummaryResponse(
                date_from=date_from,
                date_to=date_to,
                currency=self._to_currency_model(currency),
                inflow_total=total.inflow_total,
                outflow_total=total.outflow_total,
                net_cash_flow=total.net_cash_flow,
                allocations_count=total.allocations_count,
                inflow_count=total.inflow_count,
                outflow_count=total.outflow_count,
                diagnostics=diagnostics,
                totals_by_currency=[
                    BddsReportTotalsByCurrencyItem(
                        currency=self._to_currency_model(currency),
                        inflow_total=total.inflow_total,
                        outflow_total=total.outflow_total,
                        net_cash_flow=total.net_cash_flow,
                    )
                ]
                if currency is not None
                else [],
            )

        aggregate_all = self._aggregate_totals(included)
        return BddsReportSummaryResponse(
            date_from=date_from,
            date_to=date_to,
            currency=None,
            inflow_total=None,
            outflow_total=None,
            net_cash_flow=None,
            allocations_count=aggregate_all.allocations_count,
            inflow_count=aggregate_all.inflow_count,
            outflow_count=aggregate_all.outflow_count,
            diagnostics=diagnostics,
            totals_by_currency=[
                BddsReportTotalsByCurrencyItem(
                    currency=self._to_currency_model(currency),
                    inflow_total=totals.inflow_total,
                    outflow_total=totals.outflow_total,
                    net_cash_flow=totals.net_cash_flow,
                )
                for currency, totals in totals_by_currency
            ],
        )

    def get_by_items(
        self,
        *,
        current_user,
        date_from: date,
        date_to: date,
        organization_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        cash_flow_operation_type_id: UUID | None,
        currency_id: UUID | None,
    ) -> BddsReportByItemsResponse:
        self._require_permission(current_user.id, "cash_flow.report.read")
        self._validate_period(date_from, date_to)
        records = self._included_records(
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id,
            project_id=project_id,
            cash_flow_item_id=cash_flow_item_id,
            cash_flow_operation_type_id=cash_flow_operation_type_id,
            currency_id=currency_id,
        )
        grouped: dict[tuple[UUID, UUID], tuple[_NormalizedAllocation, _Totals]] = {}
        for record in records:
            assert record.cash_flow_item is not None
            assert record.currency is not None
            key = (record.cash_flow_item.id, record.currency.id)
            sample, totals = grouped.get(key, (record, _Totals()))
            self._apply_record(totals, record)
            grouped[key] = (sample, totals)

        items = [
            BddsReportByItemRow(
                cash_flow_item=self._to_lookup_model(sample.cash_flow_item),
                currency=self._to_currency_model(sample.currency),
                inflow_total=totals.inflow_total,
                outflow_total=totals.outflow_total,
                net_cash_flow=totals.net_cash_flow,
                allocations_count=totals.allocations_count,
            )
            for sample, totals in grouped.values()
        ]
        items.sort(key=lambda row: (row.cash_flow_item.direction or "", row.cash_flow_item.name.lower(), row.currency.code if row.currency else ""))
        return BddsReportByItemsResponse(items=items, total=len(items))

    def get_by_projects(
        self,
        *,
        current_user,
        date_from: date,
        date_to: date,
        organization_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        cash_flow_operation_type_id: UUID | None,
        currency_id: UUID | None,
    ) -> BddsReportByProjectsResponse:
        self._require_permission(current_user.id, "cash_flow.report.read")
        self._validate_period(date_from, date_to)
        records = self._included_records(
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id,
            project_id=project_id,
            cash_flow_item_id=cash_flow_item_id,
            cash_flow_operation_type_id=cash_flow_operation_type_id,
            currency_id=currency_id,
        )
        grouped: dict[tuple[UUID | None, UUID], tuple[_NormalizedAllocation, _Totals]] = {}
        for record in records:
            assert record.currency is not None
            project_key = record.project.id if record.project is not None else None
            key = (project_key, record.currency.id)
            sample, totals = grouped.get(key, (record, _Totals()))
            self._apply_record(totals, record)
            grouped[key] = (sample, totals)

        items = [
            BddsReportByProjectRow(
                project=self._to_lookup_model(sample.project) if sample.project is not None else None,
                project_name=sample.project.name if sample.project is not None else "Без проекта",
                currency=self._to_currency_model(sample.currency),
                inflow_total=totals.inflow_total,
                outflow_total=totals.outflow_total,
                net_cash_flow=totals.net_cash_flow,
                allocations_count=totals.allocations_count,
            )
            for sample, totals in grouped.values()
        ]
        items.sort(key=lambda row: (row.project_name.lower(), row.currency.code if row.currency else ""))
        return BddsReportByProjectsResponse(items=items, total=len(items))

    def get_by_organizations(
        self,
        *,
        current_user,
        date_from: date,
        date_to: date,
        organization_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        cash_flow_operation_type_id: UUID | None,
        currency_id: UUID | None,
    ) -> BddsReportByOrganizationsResponse:
        self._require_permission(current_user.id, "cash_flow.report.read")
        self._validate_period(date_from, date_to)
        records = self._included_records(
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id,
            project_id=project_id,
            cash_flow_item_id=cash_flow_item_id,
            cash_flow_operation_type_id=cash_flow_operation_type_id,
            currency_id=currency_id,
        )
        grouped: dict[tuple[UUID, UUID], tuple[_NormalizedAllocation, _Totals]] = {}
        for record in records:
            if record.organization is None:
                continue
            assert record.currency is not None
            key = (record.organization.id, record.currency.id)
            sample, totals = grouped.get(key, (record, _Totals()))
            self._apply_record(totals, record)
            grouped[key] = (sample, totals)

        items = [
            BddsReportByOrganizationRow(
                organization=self._to_lookup_model(sample.organization),
                currency=self._to_currency_model(sample.currency),
                inflow_total=totals.inflow_total,
                outflow_total=totals.outflow_total,
                net_cash_flow=totals.net_cash_flow,
                allocations_count=totals.allocations_count,
            )
            for sample, totals in grouped.values()
        ]
        items.sort(key=lambda row: (row.organization.name.lower(), row.currency.code if row.currency else ""))
        return BddsReportByOrganizationsResponse(items=items, total=len(items))

    def get_by_periods(
        self,
        *,
        current_user,
        date_from: date,
        date_to: date,
        organization_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        cash_flow_operation_type_id: UUID | None,
        currency_id: UUID | None,
        group_period: str | None,
    ) -> BddsReportByPeriodsResponse:
        self._require_permission(current_user.id, "cash_flow.report.read")
        self._validate_period(date_from, date_to)
        resolved_group_period = self._resolve_group_period(group_period)
        records = self._included_records(
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id,
            project_id=project_id,
            cash_flow_item_id=cash_flow_item_id,
            cash_flow_operation_type_id=cash_flow_operation_type_id,
            currency_id=currency_id,
        )
        grouped: dict[tuple[date, date, UUID], tuple[_NormalizedAllocation, _Totals]] = {}
        for record in records:
            assert record.source_document_date is not None
            assert record.currency is not None
            period_start, period_end = self._period_bounds(record.source_document_date, resolved_group_period)
            key = (period_start, period_end, record.currency.id)
            sample, totals = grouped.get(key, (record, _Totals()))
            self._apply_record(totals, record)
            grouped[key] = (sample, totals)

        items = [
            BddsReportByPeriodRow(
                period_start=period_start,
                period_end=period_end,
                currency=self._to_currency_model(sample.currency),
                inflow_total=totals.inflow_total,
                outflow_total=totals.outflow_total,
                net_cash_flow=totals.net_cash_flow,
                allocations_count=totals.allocations_count,
            )
            for (period_start, period_end, _), (sample, totals) in grouped.items()
        ]
        items.sort(key=lambda row: (row.period_start, row.currency.code if row.currency else ""))
        return BddsReportByPeriodsResponse(group_period=resolved_group_period, items=items, total=len(items))

    def get_diagnostics(
        self,
        *,
        current_user,
        date_from: date,
        date_to: date,
        organization_id: UUID | None,
        project_id: UUID | None,
        currency_id: UUID | None,
        diagnostic_type: DiagnosticType | None,
        limit: int,
        offset: int,
    ) -> BddsReportDiagnosticsResponse:
        self._require_permission(current_user.id, "cash_flow.report.read")
        self._validate_period(date_from, date_to)
        records = self._filtered_records(
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id,
            project_id=project_id,
            cash_flow_item_id=None,
            cash_flow_operation_type_id=None,
            currency_id=currency_id,
            include_missing_date_records=True,
        )
        items: list[BddsReportDiagnosticRow] = []
        for record in records:
            for row_type in record.diagnostic_types:
                if diagnostic_type is not None and row_type != diagnostic_type:
                    continue
                items.append(
                    BddsReportDiagnosticRow(
                        document_id=record.document_id,
                        source_document_number=record.source_document_number,
                        source_document_date=record.source_document_date,
                        source_document_type_1c=record.source_document_type_1c,
                        diagnostic_type=row_type,
                        allocation_status=record.allocation_status,
                        message=DIAGNOSTIC_MESSAGES[row_type],
                    )
                )
        items.sort(key=lambda row: (row.source_document_date or date.min, str(row.document_id), row.diagnostic_type))
        total = len(items)
        return BddsReportDiagnosticsResponse(items=items[offset : offset + limit], total=total, limit=limit, offset=offset)

    def _filtered_records(
        self,
        *,
        date_from: date,
        date_to: date,
        organization_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        cash_flow_operation_type_id: UUID | None,
        currency_id: UUID | None,
        include_missing_date_records: bool = False,
    ) -> list[_NormalizedAllocation]:
        records = [self._normalize_document(document) for document in self.repository.list_cash_flow_allocation_documents()]
        return [
            record
            for record in records
            if self._matches_filters(
                record,
                date_from=date_from,
                date_to=date_to,
                organization_id=organization_id,
                project_id=project_id,
                cash_flow_item_id=cash_flow_item_id,
                cash_flow_operation_type_id=cash_flow_operation_type_id,
                currency_id=currency_id,
                include_missing_date_records=include_missing_date_records,
            )
        ]

    def _included_records(self, **kwargs) -> list[_NormalizedAllocation]:
        return [record for record in self._filtered_records(**kwargs) if record.included_in_report]

    def _normalize_document(self, document) -> _NormalizedAllocation:
        data = document.data_json or {}
        allocation_status = str(data.get("allocation_status") or "Draft")
        source_document_date = self._parse_date(data.get("source_document_date"))
        cash_flow_direction = data.get("cash_flow_direction") if data.get("cash_flow_direction") in {"Inflow", "Outflow"} else None
        amount = self._parse_decimal(data.get("amount"))
        organization = self._lookup(self.repository.get_organization(self._parse_uuid(data.get("organization_id"))))
        project = self._lookup(self.repository.get_project(self._parse_uuid(data.get("project_id"))))
        cash_flow_item = self._lookup(self.repository.get_cash_flow_item(self._parse_uuid(data.get("cash_flow_item_id"))))
        cash_flow_operation_type = self._lookup(
            self.repository.get_cash_flow_operation_type(self._parse_uuid(data.get("cash_flow_operation_type_id")))
        )
        currency = self._lookup_currency(self._parse_uuid(data.get("currency_id")))

        diagnostic_types: list[DiagnosticType] = []
        if allocation_status == "NeedsEnrichment":
            diagnostic_types.append("needs_enrichment")
        if allocation_status == "Ignored":
            diagnostic_types.append("ignored")
        if source_document_date is None:
            diagnostic_types.append("missing_date")
        if cash_flow_direction is None:
            diagnostic_types.append("missing_direction")
        if amount is None or amount == ZERO:
            diagnostic_types.append("missing_amount")
        if cash_flow_item is None:
            diagnostic_types.append("missing_cash_flow_item")
        if currency is None:
            diagnostic_types.append("missing_currency")
        if bool(data.get("source_changed")):
            diagnostic_types.append("source_changed")

        included_in_report = (
            allocation_status == "Completed"
            and source_document_date is not None
            and cash_flow_direction in {"Inflow", "Outflow"}
            and amount is not None
            and amount != ZERO
            and cash_flow_item is not None
            and currency is not None
        )
        return _NormalizedAllocation(
            document_id=document.id,
            allocation_status=allocation_status,
            source_document_number=data.get("source_document_number"),
            source_document_type_1c=data.get("source_document_type_1c"),
            source_document_date=source_document_date,
            cash_flow_direction=cash_flow_direction,
            organization=organization,
            project=project,
            cash_flow_item=cash_flow_item,
            cash_flow_operation_type=cash_flow_operation_type,
            currency=currency,
            amount=amount,
            source_changed=bool(data.get("source_changed")),
            diagnostic_types=diagnostic_types,
            included_in_report=included_in_report,
        )

    def _matches_filters(
        self,
        record: _NormalizedAllocation,
        *,
        date_from: date,
        date_to: date,
        organization_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        cash_flow_operation_type_id: UUID | None,
        currency_id: UUID | None,
        include_missing_date_records: bool,
    ) -> bool:
        if organization_id and (record.organization is None or record.organization.id != organization_id):
            return False
        if project_id and (record.project is None or record.project.id != project_id):
            return False
        if cash_flow_item_id and (record.cash_flow_item is None or record.cash_flow_item.id != cash_flow_item_id):
            return False
        if cash_flow_operation_type_id and (
            record.cash_flow_operation_type is None or record.cash_flow_operation_type.id != cash_flow_operation_type_id
        ):
            return False
        if currency_id and (record.currency is None or record.currency.id != currency_id):
            return False
        if record.source_document_date is not None:
            return date_from <= record.source_document_date <= date_to
        return include_missing_date_records and "missing_date" in record.diagnostic_types

    def _aggregate_totals(self, records: Iterable[_NormalizedAllocation]) -> _Totals:
        totals = _Totals()
        for record in records:
            self._apply_record(totals, record)
        return totals

    def _apply_record(self, totals: _Totals, record: _NormalizedAllocation) -> None:
        assert record.amount is not None
        totals.allocations_count += 1
        if record.cash_flow_direction == "Inflow":
            totals.inflow_total += record.amount
            totals.inflow_count += 1
        elif record.cash_flow_direction == "Outflow":
            totals.outflow_total += record.amount
            totals.outflow_count += 1

    def _totals_by_currency(self, records: Iterable[_NormalizedAllocation]) -> list[tuple[_Currency | None, _Totals]]:
        grouped: dict[UUID | None, tuple[_Currency | None, _Totals]] = {}
        for record in records:
            currency_key = record.currency.id if record.currency is not None else None
            sample_currency, totals = grouped.get(currency_key, (record.currency, _Totals()))
            self._apply_record(totals, record)
            grouped[currency_key] = (sample_currency, totals)
        items = list(grouped.values())
        items.sort(key=lambda item: item[0].code if item[0] is not None else "")
        return items

    def _resolve_group_period(self, value: str | None) -> GroupPeriod:
        candidate = value or "month"
        if candidate not in VALID_GROUP_PERIODS:
            raise AppError(
                "group_period must be one of day, week, month, quarter, year",
                code="BDDS_REPORT_INVALID_GROUP_PERIOD",
                status_code=422,
            )
        return candidate  # type: ignore[return-value]

    def _validate_period(self, date_from: date, date_to: date) -> None:
        if date_from > date_to:
            raise AppError(
                "date_from must be less than or equal to date_to",
                code="BDDS_REPORT_INVALID_PERIOD",
                status_code=422,
            )
        if date_from + timedelta(days=365 * 5) < date_to:
            raise AppError(
                "BDDS report period cannot be longer than 5 years",
                code="BDDS_REPORT_PERIOD_TOO_LONG",
                status_code=422,
            )

    def _period_bounds(self, value: date, group_period: GroupPeriod) -> tuple[date, date]:
        if group_period == "day":
            return value, value
        if group_period == "week":
            start = value - timedelta(days=value.weekday())
            end = start + timedelta(days=6)
            return start, end
        if group_period == "month":
            start = value.replace(day=1)
            next_month = self._add_months(start, 1)
            return start, next_month - timedelta(days=1)
        if group_period == "quarter":
            quarter_month = ((value.month - 1) // 3) * 3 + 1
            start = value.replace(month=quarter_month, day=1)
            next_quarter = self._add_months(start, 3)
            return start, next_quarter - timedelta(days=1)
        start = value.replace(month=1, day=1)
        end = value.replace(month=12, day=31)
        return start, end

    def _add_months(self, value: date, months: int) -> date:
        month = value.month - 1 + months
        year = value.year + month // 12
        month = month % 12 + 1
        return value.replace(year=year, month=month, day=1)

    def _lookup(self, model) -> _Lookup | None:
        if model is None:
            return None
        return _Lookup(
            id=model.id,
            code=getattr(model, "code", None),
            name=model.name,
            direction=getattr(model, "direction", None),
        )

    def _lookup_currency(self, currency_id: UUID | None) -> _Currency | None:
        model = self.repository.get_currency(currency_id)
        if model is None:
            return None
        return _Currency(id=model.id, code=model.code, name=model.name)

    def _to_lookup_model(self, value: _Lookup | None) -> BddsReportLookup:
        assert value is not None
        return BddsReportLookup(id=value.id, code=value.code, name=value.name, direction=value.direction)

    def _to_currency_model(self, value: _Currency | None) -> BddsReportCurrency | None:
        if value is None:
            return None
        return BddsReportCurrency(id=value.id, code=value.code, name=value.name)

    def _parse_uuid(self, value) -> UUID | None:
        if value in (None, ""):
            return None
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None

    def _parse_date(self, value) -> date | None:
        if value in (None, ""):
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None

    def _parse_decimal(self, value) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    def _require_permission(self, user_id: UUID, permission_code: str) -> None:
        permissions = get_user_permission_codes(self.repository.db, user_id)
        if "admin.access" in permissions or permission_code in permissions:
            return
        raise AppError(
            "Permission required",
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"permission": permission_code},
        )
