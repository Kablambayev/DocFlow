from __future__ import annotations

from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentTypeCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    is_system: bool = False
    is_active: bool = True


class DocumentTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    is_system: bool | None = None
    is_active: bool | None = None


class DocumentTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DocumentTypeVersionCreate(BaseModel):
    schema_payload: dict = Field(alias="schema_json")


class DocumentTypeVersionUpdate(BaseModel):
    schema_payload: dict | None = Field(default=None, alias="schema_json")


class DocumentTypeVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type_id: UUID
    version_number: int
    status: str
    schema_payload: dict = Field(alias="schema_json")
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class DocumentTypeSectionRequest(BaseModel):
    code: str
    name: str
    sort_order: int = Field(default=10, alias="sortOrder")


FieldType = Literal[
    "string",
    "text",
    "integer",
    "decimal",
    "money",
    "date",
    "datetime",
    "boolean",
    "enum",
    "dictionary",
    "reference",
    "file",
    "table",
]


class DocumentTypeFieldRequest(BaseModel):
    section_code: str = Field(alias="sectionCode")
    code: str
    name: str
    type: FieldType
    required: bool = False
    readonly: bool = False
    sort_order: int = Field(default=10, alias="sortOrder")
    settings: dict = Field(default_factory=dict)
    validation: dict = Field(default_factory=dict)


class SchemaValidationError(BaseModel):
    field: str | None = None
    message: str


class SchemaValidationResult(BaseModel):
    valid: bool
    errors: list[SchemaValidationError]
