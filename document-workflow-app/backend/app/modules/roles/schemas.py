from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None


class RoleCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    is_active: bool = True


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    permissions: list[PermissionRead] = []


class RolePermissionRequest(BaseModel):
    permission_id: UUID


class UserRoleRequest(BaseModel):
    role_id: UUID
