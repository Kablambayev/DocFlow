from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    user_id: UUID | None
    old_values_json: dict | None
    new_values_json: dict | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

