from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.documents.models import DocumentApprovalStatus
from app.modules.integration.one_c.payment_export_models import PaymentRequest1CExportStatus
from app.modules.treasury.repository import TreasuryRepository
from app.modules.treasury.schemas import (
    TreasuryCurrencyItem,
    TreasuryExportInfo,
    TreasuryLookupItem,
    TreasuryMetricsResponse,
    TreasuryPaymentRequestRead,
    TreasuryPaymentRequestsResponse,
    TreasuryProjectItem,
)


class TreasuryService:
    def __init__(self, repository: TreasuryRepository):
        self.repository = repository

    def list_payment_requests(
        self,
        *,
        export_status: str | None,
        approval_status: str,
        organization_id: UUID | None,
        counterparty_id: UUID | None,
        project_id: UUID | None,
        currency_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        amount_from: Decimal | None,
        amount_to: Decimal | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> TreasuryPaymentRequestsResponse:
        items = self._load_registry_items(approval_status)
        filtered = [
            item
            for item in items
            if self._matches_filters(
                item,
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
            )
        ]
        total = len(filtered)
        ordered = self._sort_items(filtered, sort_by=sort_by, sort_order=sort_order)
        return TreasuryPaymentRequestsResponse(items=ordered[offset : offset + limit], total=total, limit=limit, offset=offset)

    def get_metrics(self) -> TreasuryMetricsResponse:
        items = self._load_registry_items(DocumentApprovalStatus.APPROVED)
        ready_to_send = [item for item in items if item.export is None]
        created_in_1c = [item for item in items if item.export is not None and item.export.status == PaymentRequest1CExportStatus.CREATED_IN_1C]
        already_exists_in_1c = [item for item in items if item.export is not None and item.export.status == PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C]
        failed = [item for item in items if item.export is not None and item.export.status == PaymentRequest1CExportStatus.FAILED]
        return TreasuryMetricsResponse(
            ready_to_send=len(ready_to_send),
            created_in_1c=len(created_in_1c),
            already_exists_in_1c=len(already_exists_in_1c),
            failed=len(failed),
            total_amount_ready=sum((item.amount or Decimal("0")) for item in ready_to_send),
            total_amount_created_in_1c=sum((item.amount or Decimal("0")) for item in created_in_1c),
        )

    def _load_registry_items(self, approval_status: str) -> list[TreasuryPaymentRequestRead]:
        documents = self.repository.list_payment_request_documents(approval_status)
        exports = self.repository.get_exports_by_document_ids([document.id for document in documents])
        approved_dates = self.repository.get_approved_at_by_document_ids(documents)
        data_items = [document.data_json or {} for document in documents]

        def ids_for(field: str) -> set[UUID]:
            return {
                item_id
                for data in data_items
                if (item_id := self.repository.parse_uuid(data.get(field))) is not None
            }

        lookups = {
            "organizations": self.repository.get_organizations(ids_for("organization_id")),
            "counterparties": self.repository.get_counterparties(ids_for("counterparty_id")),
            "contracts": self.repository.get_contracts(ids_for("contract_id")),
            "currencies": self.repository.get_currencies(ids_for("currency_id")),
            "projects": self.repository.get_projects(ids_for("project_id")),
            "expense_items": self.repository.get_expense_items(ids_for("expense_item_id")),
        }
        return [
            self._build_registry_item(document, exports.get(document.id), approved_dates[document.id], lookups)
            for document in documents
        ]

    def _build_registry_item(self, document, export, approved_at, lookups) -> TreasuryPaymentRequestRead:
        data = document.data_json or {}
        organization = lookups["organizations"].get(self.repository.parse_uuid(data.get("organization_id")))
        counterparty = lookups["counterparties"].get(self.repository.parse_uuid(data.get("counterparty_id")))
        contract = lookups["contracts"].get(self.repository.parse_uuid(data.get("contract_id")))
        currency = lookups["currencies"].get(self.repository.parse_uuid(data.get("currency_id")))
        project = lookups["projects"].get(self.repository.parse_uuid(data.get("project_id")))
        expense_item = lookups["expense_items"].get(self.repository.parse_uuid(data.get("expense_item_id")))
        return TreasuryPaymentRequestRead(
            document_id=document.id,
            number=document.number,
            title=document.title,
            document_date=document.document_date,
            approved_at=approved_at,
            organization=self._lookup_item(organization),
            counterparty=self._lookup_item(counterparty),
            contract=self._lookup_item(contract),
            currency=TreasuryCurrencyItem(id=currency.id, code=currency.code, name=currency.name) if currency is not None else None,
            project=TreasuryProjectItem(id=project.id, code=project.code, name=project.name) if project is not None else None,
            expense_item=self._lookup_item(expense_item),
            amount=self.repository.parse_decimal(data.get("amount")),
            payment_purpose=data.get("payment_purpose") or data.get("paymentPurpose"),
            export=self._export_item(export),
            approval_status=document.approval_status,
        )

    def _lookup_item(self, item) -> TreasuryLookupItem | None:
        if item is None:
            return None
        return TreasuryLookupItem(id=item.id, name=item.name)

    def _export_item(self, export) -> TreasuryExportInfo | None:
        if export is None:
            return None
        return TreasuryExportInfo(
            status=export.status,
            sent_at=export.sent_at,
            one_c_payment_order_external_id=export.one_c_payment_order_external_id,
            one_c_payment_order_number=export.one_c_payment_order_number,
            one_c_payment_order_date=export.one_c_payment_order_date,
            one_c_payment_order_amount=export.one_c_payment_order_amount,
            one_c_payment_order_currency_code=export.one_c_payment_order_currency_code,
            error_code=export.error_code,
            error_message=export.error_message,
        )

    def _matches_filters(
        self,
        item: TreasuryPaymentRequestRead,
        *,
        export_status: str | None,
        approval_status: str,
        organization_id: UUID | None,
        counterparty_id: UUID | None,
        project_id: UUID | None,
        currency_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        amount_from: Decimal | None,
        amount_to: Decimal | None,
        search: str | None,
    ) -> bool:
        if item.approval_status != approval_status:
            return False
        if export_status == "not_exported" and item.export is not None:
            return False
        if export_status not in [None, "not_exported"] and (item.export is None or item.export.status != export_status):
            return False
        if organization_id is not None and (item.organization is None or item.organization.id != organization_id):
            return False
        if counterparty_id is not None and (item.counterparty is None or item.counterparty.id != counterparty_id):
            return False
        if project_id is not None and (item.project is None or item.project.id != project_id):
            return False
        if currency_id is not None and (item.currency is None or item.currency.id != currency_id):
            return False
        if date_from is not None and (item.document_date is None or item.document_date.date() < date_from):
            return False
        if date_to is not None and (item.document_date is None or item.document_date.date() > date_to):
            return False
        if amount_from is not None and (item.amount is None or item.amount < amount_from):
            return False
        if amount_to is not None and (item.amount is None or item.amount > amount_to):
            return False
        if search:
            needle = search.strip().lower()
            if needle and needle not in (item.number or "").lower() and needle not in (item.title or "").lower():
                return False
        return True

    def _sort_items(self, items: list[TreasuryPaymentRequestRead], *, sort_by: str, sort_order: str) -> list[TreasuryPaymentRequestRead]:
        reverse = sort_order.lower() == "desc"

        def sort_key(item: TreasuryPaymentRequestRead):
            if sort_by == "document_date":
                return item.document_date or item.approved_at
            if sort_by == "amount":
                return item.amount or Decimal("0")
            if sort_by == "number":
                return item.number
            return item.approved_at or item.document_date

        return sorted(items, key=sort_key, reverse=reverse)
