from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class CashFlowDocumentDictionaryRef(BaseModel):
    external_id: str | None = None
    code: str | None = None
    name: str | None = None


class CashFlowDocumentImportItem(BaseModel):
    external_id: str
    source_document_type_1c: str
    source_document_type: str | None = None
    cash_flow_direction: str | None = None
    number: str
    date: date
    posted_at: datetime | None = None
    organization: CashFlowDocumentDictionaryRef | None = None
    counterparty: CashFlowDocumentDictionaryRef | None = None
    contract: CashFlowDocumentDictionaryRef | None = None
    currency: CashFlowDocumentDictionaryRef | None = None
    amount: Decimal
    payment_purpose: str | None = None
    comment: str | None = None
    project: CashFlowDocumentDictionaryRef | None = None
    cash_flow_item: CashFlowDocumentDictionaryRef | None = None
    is_deleted: bool = False
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CashFlowDocumentsImportEnvelope(BaseModel):
    source_system: str = Field(default="1C", description="Source accounting system code")
    items: list[dict[str, Any]] = Field(default_factory=list, description="Items to import")


class CashFlowDocumentsImportItemError(BaseModel):
    index: int
    external_id: str | None = None
    code: str
    message: str
    details: dict[str, Any] | None = None


class CashFlowDocumentsImportResult(BaseModel):
    status: str = "completed"
    source_system: str
    entity: str = "cash_flow_documents"
    received: int
    created: int
    updated: int
    skipped: int
    completed: int
    needs_enrichment: int
    errors: list[CashFlowDocumentsImportItemError] = Field(default_factory=list)
