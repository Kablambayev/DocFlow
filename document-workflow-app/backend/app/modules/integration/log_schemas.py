from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


IntegrationDirection = Literal["Inbound", "Outbound"]
IntegrationLogStatus = Literal["Started", "Success", "PartialSuccess", "Failed", "Skipped"]


class IntegrationLogListItem(BaseModel):
    id: UUID
    direction: IntegrationDirection
    integration_system: str
    operation_type: str
    status: str
    document_id: UUID | None = None
    document_number: str | None = None
    initiated_by: UUID | None = None
    initiated_by_name: str | None = None
    response_status_code: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    correlation_id: str | None = None
    idempotency_key: str | None = None
    created_at: datetime


class IntegrationLogDetail(IntegrationLogListItem):
    entity_type: str | None = None
    entity_id: UUID | None = None
    request_url: str | None = None
    request_method: str | None = None
    request_headers: dict[str, Any] = Field(default_factory=dict)
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_headers: dict[str, Any] = Field(default_factory=dict)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    error_details: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None


class IntegrationLogsResponse(BaseModel):
    items: list[IntegrationLogListItem]
    total: int
    limit: int
    offset: int


class IntegrationLogRetryResponse(BaseModel):
    status: str
    export: dict[str, Any] | None = None
    one_c_enabled: bool | None = None
    payment_order: dict[str, Any] | None = None


class IntegrationLogQueryParams(BaseModel):
    direction: IntegrationDirection | None = None
    operation_type: str | None = None
    status: str | None = None
    document_id: UUID | None = None
    date_from: datetime | date | None = None
    date_to: datetime | date | None = None
    search: str | None = None
    limit: int = 50
    offset: int = 0
    sort_by: str = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"
