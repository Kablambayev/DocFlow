from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    process_id: UUID
    document_id: UUID
    step_order: int
    step_name: str
    approver_id: UUID
    status: str
    due_at: datetime | None
    created_at: datetime
    completed_at: datetime | None


class TaskDecisionRequest(BaseModel):
    comment: str | None = None


class ApprovalRouteCreate(BaseModel):
    document_type_id: UUID
    code: str
    name: str
    description: str | None = None
    is_active: bool = True


class ApprovalRouteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type_id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ApprovalRouteVersionCreate(BaseModel):
    route_schema_json: dict


class ApprovalRouteVersionUpdate(BaseModel):
    route_schema_json: dict


class ApprovalRouteVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    route_id: UUID
    version_number: int
    status: str
    route_schema_json: dict
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class ApprovalMatrixRuleCreate(BaseModel):
    document_type_id: UUID
    priority: int
    name: str
    condition_json: dict
    route_id: UUID
    is_active: bool = True


class ApprovalMatrixRuleUpdate(BaseModel):
    priority: int | None = None
    name: str | None = None
    condition_json: dict | None = None
    route_id: UUID | None = None
    is_active: bool | None = None


class ApprovalMatrixRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type_id: UUID
    priority: int
    name: str
    condition_json: dict
    route_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

