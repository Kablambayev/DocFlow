from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class ImportEnvelope(BaseModel):
    source_system: str = Field(default="1C", description="Source accounting system code")
    items: list[dict[str, Any]] = Field(default_factory=list, description="Items to import")


class ImportItemError(BaseModel):
    index: int = Field(description="Zero-based item index in request payload")
    external_id: str | None = Field(default=None, description="External identifier from source payload")
    code: str = Field(description="Machine-readable item error code")
    message: str = Field(description="Human-readable item error message")
    details: dict[str, Any] | None = Field(default=None, description="Optional structured details")


class ImportResult(BaseModel):
    status: str = Field(default="completed", description="Import completion status")
    source_system: str = Field(description="Source accounting system code")
    entity: str = Field(description="Imported dictionary entity code")
    received: int = Field(description="Total received items")
    created: int = Field(description="Number of created records")
    updated: int = Field(description="Number of updated records")
    skipped: int = Field(description="Number of skipped records")
    errors: list[ImportItemError] = Field(default_factory=list, description="Per-item import errors")


class OrganizationImportItem(BaseModel):
    external_id: str
    name: str
    code: str | None = None
    full_name: str | None = None
    is_active: bool = True
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CounterpartyImportItem(BaseModel):
    external_id: str
    name: str = Field(min_length=1)
    code: str | None = None
    full_name: str | None = None
    bin_iin: str | None = None
    is_active: bool = True
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CurrencyImportItem(BaseModel):
    external_id: str
    code: str
    name: str
    full_name: str | None = None
    numeric_code: str | None = None
    is_active: bool = True
    raw_data: dict[str, Any] = Field(default_factory=dict)


class ExpenseItemImportItem(BaseModel):
    external_id: str
    name: str
    code: str | None = None
    full_name: str | None = None
    is_active: bool = True
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CounterpartyContractImportItem(BaseModel):
    external_id: str
    organization_external_id: str
    counterparty_external_id: str
    name: str
    currency_external_id: str | None = None
    code: str | None = None
    number: str | None = None
    contract_date: date | None = None
    is_active: bool = True
    raw_data: dict[str, Any] = Field(default_factory=dict)
