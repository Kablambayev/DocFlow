from __future__ import annotations

from datetime import date as DateType, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentRegisterLookupItem(BaseModel):
    id: UUID
    name: str
    code: str | None = None


class PaymentRegisterDocumentLookupItem(PaymentRegisterLookupItem):
    number: str | None = None


class PaymentRegisterRowExportInfo(BaseModel):
    status: str | None = None
    export_id: UUID | None = None
    one_c_payment_order_external_id: str | None = None
    one_c_payment_order_number: str | None = None
    one_c_payment_order_date: DateType | None = None
    error_code: str | None = None
    error_message: str | None = None


class PaymentRegisterRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    register_id: UUID
    document_id: UUID
    row_number: int
    amount: Decimal
    payment_purpose: str | None = None
    organization: PaymentRegisterLookupItem | None = None
    counterparty: PaymentRegisterLookupItem | None = None
    contract: PaymentRegisterDocumentLookupItem | None = None
    currency: PaymentRegisterLookupItem | None = None
    project: PaymentRegisterLookupItem | None = None
    expense_item: PaymentRegisterLookupItem | None = None
    document_number: str | None = None
    document_title: str | None = None
    document_date: datetime | None = None
    approval_status: str | None = None
    export: PaymentRegisterRowExportInfo | None = None
    created_at: datetime
    updated_at: datetime


class PaymentRegisterListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str
    date: DateType
    status: str
    organization: PaymentRegisterLookupItem | None = None
    currency: PaymentRegisterLookupItem | None = None
    comment: str | None = None
    created_by: PaymentRegisterLookupItem | None = None
    sent_by: PaymentRegisterLookupItem | None = None
    sent_at: datetime | None = None
    total_amount: Decimal
    rows_count: int
    sent_rows_count: int
    failed_rows_count: int
    created_at: datetime
    updated_at: datetime


class PaymentRegisterDetailRead(PaymentRegisterListItem):
    rows: list[PaymentRegisterRowRead] = Field(default_factory=list)


class PaymentRegistersResponse(BaseModel):
    items: list[PaymentRegisterListItem]
    total: int
    limit: int
    offset: int


class PaymentRegisterCreate(BaseModel):
    number: str | None = None
    date: DateType
    organization_id: UUID | None = None
    currency_id: UUID | None = None
    comment: str | None = None


class PaymentRegisterUpdate(BaseModel):
    number: str | None = None
    date: DateType | None = None
    organization_id: UUID | None = None
    currency_id: UUID | None = None
    comment: str | None = None


class PaymentRegisterRowsAddRequest(BaseModel):
    document_ids: list[UUID]


class PaymentRegisterRowAddError(BaseModel):
    document_id: UUID
    code: str
    message: str


class PaymentRegisterRowsAddResponse(BaseModel):
    payment_register: PaymentRegisterDetailRead
    added_count: int
    skipped_document_ids: list[UUID]
    errors: list[PaymentRegisterRowAddError]


class PaymentRegisterActionResponse(BaseModel):
    payment_register: PaymentRegisterDetailRead


class PaymentRegisterSendRowResult(BaseModel):
    row_id: UUID
    document_id: UUID
    export_status: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class PaymentRegisterSendResponse(BaseModel):
    payment_register: PaymentRegisterDetailRead
    processed_rows_count: int
    skipped_rows_count: int
    results: list[PaymentRegisterSendRowResult]


class PaymentRegisterAvailableRequestRead(BaseModel):
    document_id: UUID
    number: str
    title: str | None = None
    document_date: datetime | None = None
    approved_at: datetime | None = None
    organization: PaymentRegisterLookupItem | None = None
    counterparty: PaymentRegisterLookupItem | None = None
    contract: PaymentRegisterDocumentLookupItem | None = None
    currency: PaymentRegisterLookupItem | None = None
    project: PaymentRegisterLookupItem | None = None
    expense_item: PaymentRegisterLookupItem | None = None
    amount: Decimal | None = None
    payment_purpose: str | None = None
    export_status: str | None = None
    export_error_code: str | None = None
    export_error_message: str | None = None


class PaymentRegisterAvailableRequestsResponse(BaseModel):
    items: list[PaymentRegisterAvailableRequestRead]
    total: int
    limit: int
    offset: int
