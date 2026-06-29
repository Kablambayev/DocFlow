from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class TreasuryLookupItem(BaseModel):
    id: UUID
    name: str


class TreasuryCurrencyItem(TreasuryLookupItem):
    code: str


class TreasuryProjectItem(TreasuryLookupItem):
    code: str | None = None


class TreasuryExportInfo(BaseModel):
    status: str
    sent_at: datetime | None = None
    one_c_payment_order_external_id: str | None = None
    one_c_payment_order_number: str | None = None
    one_c_payment_order_date: date | None = None
    one_c_payment_order_amount: Decimal | None = None
    one_c_payment_order_currency_code: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class TreasuryPaymentRequestRead(BaseModel):
    document_id: UUID
    number: str
    title: str | None = None
    document_date: datetime | None = None
    approved_at: datetime | None = None
    organization: TreasuryLookupItem | None = None
    counterparty: TreasuryLookupItem | None = None
    contract: TreasuryLookupItem | None = None
    currency: TreasuryCurrencyItem | None = None
    project: TreasuryProjectItem | None = None
    expense_item: TreasuryLookupItem | None = None
    amount: Decimal | None = None
    payment_purpose: str | None = None
    export: TreasuryExportInfo | None = None
    approval_status: str


class TreasuryPaymentRequestsResponse(BaseModel):
    items: list[TreasuryPaymentRequestRead]
    total: int
    limit: int
    offset: int


class TreasuryMetricsResponse(BaseModel):
    ready_to_send: int
    created_in_1c: int
    already_exists_in_1c: int
    failed: int
    total_amount_ready: Decimal
    total_amount_created_in_1c: Decimal