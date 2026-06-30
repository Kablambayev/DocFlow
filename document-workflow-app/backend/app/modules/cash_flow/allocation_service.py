from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import status

from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.cash_flow.allocation_repository import CashFlowAllocationRepository
from app.modules.cash_flow.allocation_schemas import (
    CashFlowAllocationActionResponse,
    CashFlowAllocationDetailRead,
    CashFlowAllocationListItem,
    CashFlowAllocationLookupItem,
    CashFlowAllocationMetricsResponse,
    CashFlowAllocationUpdateRequest,
    CashFlowAllocationsResponse,
)
from app.modules.cash_flow.mapping_schemas import REQUIRED_COMPLETED_FIELDS


class CashFlowAllocationService:
    def __init__(self, repository: CashFlowAllocationRepository):
        self.repository = repository
        self.audit_service = AuditService(AuditRepository(repository.db))

    def list_allocations(
        self,
        *,
        current_user,
        allocation_status: str | None,
        cash_flow_direction: str | None,
        organization_id: UUID | None,
        counterparty_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        currency_id: UUID | None,
        source_changed: bool | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> CashFlowAllocationsResponse:
        self._require_permission(current_user.id, "cash_flow.allocation.read")
        items = [self._to_list_item(item) for item in self.repository.list_allocation_documents()]
        filtered = [
            item
            for item in items
            if self._matches_filters(
                item,
                allocation_status=allocation_status,
                cash_flow_direction=cash_flow_direction,
                organization_id=organization_id,
                counterparty_id=counterparty_id,
                project_id=project_id,
                cash_flow_item_id=cash_flow_item_id,
                currency_id=currency_id,
                source_changed=source_changed,
                date_from=date_from,
                date_to=date_to,
                search=search,
            )
        ]
        total = len(filtered)
        return CashFlowAllocationsResponse(items=filtered[offset : offset + limit], total=total, limit=limit, offset=offset)

    def get_metrics(self, current_user) -> CashFlowAllocationMetricsResponse:
        self._require_permission(current_user.id, "cash_flow.allocation.read")
        items = [self._to_list_item(item) for item in self.repository.list_allocation_documents()]
        return CashFlowAllocationMetricsResponse(
            needs_enrichment=sum(1 for item in items if item.allocation_status == "NeedsEnrichment"),
            completed=sum(1 for item in items if item.allocation_status == "Completed"),
            ignored=sum(1 for item in items if item.allocation_status == "Ignored"),
            source_changed=sum(1 for item in items if item.source_changed),
        )

    def get_detail(self, document_id: UUID, current_user) -> CashFlowAllocationDetailRead:
        self._require_permission(current_user.id, "cash_flow.allocation.read")
        document = self._require_document(document_id)
        return self._to_detail(document)

    def update_allocation(self, document_id: UUID, payload: CashFlowAllocationUpdateRequest, current_user) -> CashFlowAllocationDetailRead:
        self._require_permission(current_user.id, "cash_flow.allocation.manage")
        document = self._require_document(document_id)
        data = dict(document.data_json or {})
        payload_data = payload.model_dump(exclude_unset=True, mode="json")
        for key, value in payload_data.items():
            data[key] = value
        data["missing_required_fields"] = self._missing_required_fields(data)
        document.data_json = data
        self.repository.save_document(document)
        self.audit_service.log(
            "document",
            document.id,
            "cash_flow_allocation_updated",
            user_id=current_user.id,
            new_values_json=payload_data,
        )
        self.repository.db.commit()
        return self.get_detail(document.id, current_user)

    def complete(self, document_id: UUID, current_user) -> CashFlowAllocationActionResponse:
        self._require_permission(current_user.id, "cash_flow.allocation.manage")
        document = self._require_document(document_id)
        data = dict(document.data_json or {})
        missing = self._missing_required_fields(data)
        if missing:
            raise AppError(
                "Cannot complete cash flow allocation because required fields are missing",
                code="CASH_FLOW_ALLOCATION_REQUIRED_FIELDS_MISSING",
                status_code=409,
                details={"missing_required_fields": missing},
            )
        data["allocation_status"] = "Completed"
        data["missing_required_fields"] = []
        document.data_json = data
        self.repository.save_document(document)
        self.repository.db.commit()
        return CashFlowAllocationActionResponse(item=self.get_detail(document.id, current_user))

    def ignore(self, document_id: UUID, current_user) -> CashFlowAllocationActionResponse:
        self._require_permission(current_user.id, "cash_flow.allocation.manage")
        document = self._require_document(document_id)
        data = dict(document.data_json or {})
        data["allocation_status"] = "Ignored"
        document.data_json = data
        self.repository.save_document(document)
        self.repository.db.commit()
        return CashFlowAllocationActionResponse(item=self.get_detail(document.id, current_user))

    def reopen(self, document_id: UUID, current_user) -> CashFlowAllocationActionResponse:
        self._require_permission(current_user.id, "cash_flow.allocation.manage")
        document = self._require_document(document_id)
        data = dict(document.data_json or {})
        data["allocation_status"] = "NeedsEnrichment"
        data["missing_required_fields"] = self._missing_required_fields(data)
        document.data_json = data
        self.repository.save_document(document)
        self.repository.db.commit()
        return CashFlowAllocationActionResponse(item=self.get_detail(document.id, current_user))

    def _require_document(self, document_id: UUID):
        document = self.repository.get_allocation_document(document_id)
        if document is None:
            raise AppError("Cash flow allocation not found", code="CASH_FLOW_ALLOCATION_NOT_FOUND", status_code=404)
        return document

    def _to_list_item(self, document) -> CashFlowAllocationListItem:
        data = document.data_json or {}
        return CashFlowAllocationListItem(
            document_id=document.id,
            source_document_number=data.get("source_document_number"),
            source_document_date=self._parse_date(data.get("source_document_date")),
            source_document_type_1c=data.get("source_document_type_1c"),
            cash_flow_direction=data.get("cash_flow_direction"),
            organization=self._lookup(self.repository.get_organization(self._parse_uuid(data.get("organization_id")))),
            counterparty=self._lookup(self.repository.get_counterparty(self._parse_uuid(data.get("counterparty_id")))),
            project=self._lookup(self.repository.get_project(self._parse_uuid(data.get("project_id")))),
            cash_flow_item=self._lookup(self.repository.get_cash_flow_item(self._parse_uuid(data.get("cash_flow_item_id")))),
            currency=self._lookup(self.repository.get_currency(self._parse_uuid(data.get("currency_id")))),
            amount=self._parse_decimal(data.get("amount")),
            payment_purpose=data.get("payment_purpose"),
            allocation_status=data.get("allocation_status") or "Draft",
            missing_required_fields=data.get("missing_required_fields") or [],
            source_changed=bool(data.get("source_changed")),
        )

    def _to_detail(self, document) -> CashFlowAllocationDetailRead:
        data = document.data_json or {}
        return CashFlowAllocationDetailRead(
            document_id=document.id,
            document_number=document.number,
            document_date=document.document_date,
            title=document.title,
            source_system=data.get("source_system"),
            source_document_external_id=data.get("source_document_external_id"),
            source_document_type=data.get("source_document_type"),
            source_document_type_1c=data.get("source_document_type_1c"),
            source_document_number=data.get("source_document_number"),
            source_document_date=self._parse_date(data.get("source_document_date")),
            source_document_posted_at=self._parse_datetime(data.get("source_document_posted_at")),
            source_document_amount=self._parse_decimal(data.get("source_document_amount")),
            source_document_currency=self._lookup(self.repository.get_currency(self._parse_uuid(data.get("source_document_currency_id")))),
            source_document_purpose=data.get("source_document_purpose"),
            source_document_comment=data.get("source_document_comment"),
            cash_flow_direction=data.get("cash_flow_direction"),
            organization=self._lookup(self.repository.get_organization(self._parse_uuid(data.get("organization_id")))),
            counterparty=self._lookup(self.repository.get_counterparty(self._parse_uuid(data.get("counterparty_id")))),
            contract=self._lookup(self.repository.get_contract(self._parse_uuid(data.get("contract_id")))),
            currency=self._lookup(self.repository.get_currency(self._parse_uuid(data.get("currency_id")))),
            amount=self._parse_decimal(data.get("amount")),
            payment_purpose=data.get("payment_purpose"),
            cash_flow_item=self._lookup(self.repository.get_cash_flow_item(self._parse_uuid(data.get("cash_flow_item_id")))),
            project=self._lookup(self.repository.get_project(self._parse_uuid(data.get("project_id")))),
            cash_flow_operation_type=self._lookup(self.repository.get_cash_flow_operation_type(self._parse_uuid(data.get("cash_flow_operation_type_id")))),
            management_comment=data.get("management_comment"),
            allocation_status=data.get("allocation_status") or "Draft",
            missing_required_fields=data.get("missing_required_fields") or [],
            source_changed=bool(data.get("source_changed")),
            mapping_rule_id=data.get("mapping_rule_id"),
            mapping_result=data.get("mapping_result"),
            raw_source_payload=data.get("raw_source_payload") or {},
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    def _matches_filters(
        self,
        item: CashFlowAllocationListItem,
        *,
        allocation_status: str | None,
        cash_flow_direction: str | None,
        organization_id: UUID | None,
        counterparty_id: UUID | None,
        project_id: UUID | None,
        cash_flow_item_id: UUID | None,
        currency_id: UUID | None,
        source_changed: bool | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
    ) -> bool:
        if allocation_status and item.allocation_status != allocation_status:
            return False
        if cash_flow_direction and item.cash_flow_direction != cash_flow_direction:
            return False
        if organization_id and (item.organization is None or item.organization.id != organization_id):
            return False
        if counterparty_id and (item.counterparty is None or item.counterparty.id != counterparty_id):
            return False
        if project_id and (item.project is None or item.project.id != project_id):
            return False
        if cash_flow_item_id and (item.cash_flow_item is None or item.cash_flow_item.id != cash_flow_item_id):
            return False
        if currency_id and (item.currency is None or item.currency.id != currency_id):
            return False
        if source_changed is not None and item.source_changed != source_changed:
            return False
        if date_from and (item.source_document_date is None or item.source_document_date < date_from):
            return False
        if date_to and (item.source_document_date is None or item.source_document_date > date_to):
            return False
        if search:
            needle = search.strip().lower()
            haystacks = [
                item.source_document_number or "",
                item.source_document_type_1c or "",
                item.payment_purpose or "",
            ]
            if needle and not any(needle in value.lower() for value in haystacks):
                return False
        return True

    def _missing_required_fields(self, data: dict) -> list[str]:
        return sorted([field_name for field_name in REQUIRED_COMPLETED_FIELDS if data.get(field_name) in (None, "", [], {})])

    def _lookup(self, item) -> CashFlowAllocationLookupItem | None:
        if item is None:
            return None
        return CashFlowAllocationLookupItem(id=item.id, name=getattr(item, "name", None) or getattr(item, "full_name", None) or "-", code=getattr(item, "code", None))

    def _parse_uuid(self, value) -> UUID | None:
        if not isinstance(value, str):
            return None
        try:
            return UUID(value)
        except ValueError:
            return None

    def _parse_decimal(self, value) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _parse_date(self, value) -> date | None:
        if not isinstance(value, str):
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _parse_datetime(self, value) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _require_permission(self, user_id: UUID, permission_code: str) -> None:
        permissions = get_user_permission_codes(self.repository.db, user_id)
        if "admin.access" in permissions or permission_code in permissions:
            return
        raise AppError("Permission required", code="PERMISSION_DENIED", status_code=status.HTTP_403_FORBIDDEN, details={"permission": permission_code})
