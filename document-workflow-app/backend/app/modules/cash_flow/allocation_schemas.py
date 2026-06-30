from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class CashFlowAllocationLookupItem(BaseModel):
    id: UUID
    name: str
    code: str | None = None


class CashFlowAllocationListItem(BaseModel):
    document_id: UUID
    source_document_number: str | None = None
    source_document_date: date | None = None
    source_document_type_1c: str | None = None
    cash_flow_direction: str | None = None
    organization: CashFlowAllocationLookupItem | None = None
    counterparty: CashFlowAllocationLookupItem | None = None
    project: CashFlowAllocationLookupItem | None = None
    cash_flow_item: CashFlowAllocationLookupItem | None = None
    currency: CashFlowAllocationLookupItem | None = None
    amount: Decimal | None = None
    payment_purpose: str | None = None
    allocation_status: str
    missing_required_fields: list[str] = []
    source_changed: bool = False


class CashFlowAllocationsResponse(BaseModel):
    items: list[CashFlowAllocationListItem]
    total: int
    limit: int
    offset: int


class CashFlowAllocationMetricsResponse(BaseModel):
    needs_enrichment: int
    completed: int
    ignored: int
    source_changed: int


class CashFlowAllocationDetailRead(BaseModel):
    document_id: UUID
    document_number: str
    document_date: datetime
    title: str
    source_system: str | None = None
    source_document_external_id: str | None = None
    source_document_type: str | None = None
    source_document_type_1c: str | None = None
    source_document_number: str | None = None
    source_document_date: date | None = None
    source_document_posted_at: datetime | None = None
    source_document_amount: Decimal | None = None
    source_document_currency: CashFlowAllocationLookupItem | None = None
    source_document_purpose: str | None = None
    source_document_comment: str | None = None
    cash_flow_direction: str | None = None
    organization: CashFlowAllocationLookupItem | None = None
    counterparty: CashFlowAllocationLookupItem | None = None
    contract: CashFlowAllocationLookupItem | None = None
    currency: CashFlowAllocationLookupItem | None = None
    amount: Decimal | None = None
    payment_purpose: str | None = None
    cash_flow_item: CashFlowAllocationLookupItem | None = None
    project: CashFlowAllocationLookupItem | None = None
    cash_flow_operation_type: CashFlowAllocationLookupItem | None = None
    management_comment: str | None = None
    allocation_status: str
    missing_required_fields: list[str] = []
    source_changed: bool = False
    mapping_rule_id: str | None = None
    mapping_result: str | None = None
    raw_source_payload: dict = {}
    created_at: datetime
    updated_at: datetime


class CashFlowAllocationUpdateRequest(BaseModel):
    cash_flow_item_id: UUID | None = None
    project_id: UUID | None = None
    cash_flow_operation_type_id: UUID | None = None
    management_comment: str | None = None
    allocation_status: str | None = None


class CashFlowAllocationActionResponse(BaseModel):
    item: CashFlowAllocationDetailRead
