from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MAPPING_TYPES = {"path", "constant", "dictionary_lookup", "default"}
LOOKUP_BY_VALUES = {"external_id", "code", "name"}
DICTIONARY_TYPES = {
    "organization",
    "counterparty",
    "contract",
    "currency",
    "project",
    "cash_flow_operation_type",
    "cash_flow_item",
}
REQUIRED_COMPLETED_FIELDS = [
    "organization_id",
    "cash_flow_direction",
    "cash_flow_item_id",
    "currency_id",
    "amount",
    "source_document_date",
]


class CashFlowMappingRuleFieldPayload(BaseModel):
    id: UUID | None = None
    target_field: str
    mapping_type: str
    source_path: str | None = None
    constant_value: Any | None = None
    default_value: Any | None = None
    dictionary_type: str | None = None
    lookup_by: str | None = None
    is_required: bool = False
    transform: str | None = None
    sort_order: int = 100


class CashFlowMappingRuleCreate(BaseModel):
    name: str
    source_system: str = "1C"
    source_document_type_1c: str
    source_document_type_code: str
    cash_flow_direction: str
    target_document_type_code: str = "CashFlowAllocation"
    is_active: bool = True
    priority: int = 100
    description: str | None = None
    fields: list[CashFlowMappingRuleFieldPayload] = Field(default_factory=list)


class CashFlowMappingRuleUpdate(BaseModel):
    name: str | None = None
    source_system: str | None = None
    source_document_type_1c: str | None = None
    source_document_type_code: str | None = None
    cash_flow_direction: str | None = None
    target_document_type_code: str | None = None
    is_active: bool | None = None
    priority: int | None = None
    description: str | None = None
    fields: list[CashFlowMappingRuleFieldPayload] | None = None


class CashFlowMappingRuleFieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_field: str
    mapping_type: str
    source_path: str | None
    constant_value: Any | None
    default_value: Any | None
    dictionary_type: str | None
    lookup_by: str | None
    is_required: bool
    transform: str | None
    sort_order: int


class CashFlowMappingRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_system: str
    source_document_type_1c: str
    source_document_type_code: str
    cash_flow_direction: str
    target_document_type_code: str
    is_active: bool
    priority: int
    description: str | None
    fields: list[CashFlowMappingRuleFieldRead]


class CashFlowMappingRuleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_system: str
    source_document_type_1c: str
    source_document_type_code: str
    cash_flow_direction: str
    target_document_type_code: str
    is_active: bool
    priority: int
    description: str | None
    fields_count: int


class CashFlowMappingTestRequest(BaseModel):
    source_payload: dict[str, Any]


class CashFlowMappingFieldResult(BaseModel):
    target_field: str
    mapping_type: str
    source_path: str | None = None
    source_value: Any | None = None
    mapped_value: Any | None = None
    status: str
    message: str | None = None


class CashFlowMappingResult(BaseModel):
    rule_id: UUID
    status: str
    mapped_data: dict[str, Any]
    missing_required_fields: list[str]
    field_results: list[CashFlowMappingFieldResult]
