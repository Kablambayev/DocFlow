from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type_id: UUID
    document_type_version_id: UUID
    number: str
    document_date: datetime
    author_id: UUID
    organization_id: UUID | None
    department_id: UUID | None
    approval_status: str
    business_status: str | None
    title: str
    data_json: dict
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    document_type_id: UUID
    document_type_version_id: UUID
    number: str
    document_date: datetime
    author_id: UUID
    organization_id: UUID | None = None
    department_id: UUID | None = None
    title: str
    data_json: dict | None = None


class DocumentUpdate(BaseModel):
    number: str | None = None
    document_date: datetime | None = None
    organization_id: UUID | None = None
    department_id: UUID | None = None
    title: str | None = None
    data_json: dict | None = None


class DocumentSubmitRequest(BaseModel):
    user_id: UUID | None = None


class DocumentWithdrawRequest(BaseModel):
    user_id: UUID | None = None

