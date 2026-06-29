from __future__ import annotations

from datetime import date as DateType, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentOrderInfo(BaseModel):
    external_id: str | None = None
    number: str | None = None
    date: DateType | None = None
    amount: Decimal | None = None
    currency_code: str | None = None


class ExportErrorInfo(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class PaymentRequest1CExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    status: str
    sent_at: datetime | None = None
    sent_by: UUID | None = None
    one_c_payment_order_external_id: str | None = None
    one_c_payment_order_number: str | None = None
    one_c_payment_order_date: DateType | None = None
    one_c_payment_order_amount: Decimal | None = None
    one_c_payment_order_currency_code: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class PaymentRequest1CExportStatusResponse(BaseModel):
    status: str


class PaymentRequest1CExportNotExportedResponse(PaymentRequest1CExportStatusResponse):
    status: str = "not_exported"


class PaymentRequest1CSendResponse(BaseModel):
    status: str
    document_id: UUID
    sent_at: datetime | None = None
    one_c_enabled: bool
    payment_order: PaymentOrderInfo | None = None
    error: ExportErrorInfo | None = None


class PaymentRequest1CAlreadyExportedResponse(BaseModel):
    status: str = "already_exported"
    export: PaymentRequest1CExportRead


class PaymentRequest1CPayload(BaseModel):
    request_id: UUID
    request_number: str
    request_date: DateType
    organization_external_id: str
    counterparty_external_id: str
    contract_external_id: str
    currency_external_id: str
    expense_item_external_id: str
    cash_flow_operation_type_code: str
    project_code: str
    amount: Decimal
    payment_purpose: str | None = None
    comment: str | None = None
    author: dict[str, Any]
    approved_at: datetime


class PaymentRequest1CClientResult(BaseModel):
    status: str
    payment_order: dict[str, Any] | None = None
    error: ExportErrorInfo | None = None
    one_c_enabled: bool = Field(default=True)