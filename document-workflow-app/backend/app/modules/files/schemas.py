from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    field_code: str | None
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by: UUID
    uploaded_at: datetime


class DeleteFileResponse(BaseModel):
    status: str = "deleted"
