from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentCommentCreate(BaseModel):
    comment_text: str
    parent_comment_id: UUID | None = None


class DocumentCommentUpdate(BaseModel):
    comment_text: str


class DocumentCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    author_id: UUID
    author_name: str | None = None
    comment_text: str
    comment_type: str
    parent_comment_id: UUID | None
    created_at: datetime
    updated_at: datetime | None


class DeleteCommentResponse(BaseModel):
    status: str = "deleted"


class TimelineItem(BaseModel):
    id: str
    type: str
    title: str
    description: str | None = None
    user_id: UUID | None = None
    user_name: str | None = None
    created_at: datetime
    payload: dict = {}


class ApprovalTaskTimelineRead(BaseModel):
    id: UUID
    approver_id: UUID
    approver_name: str | None = None
    status: str
    created_at: datetime
    completed_at: datetime | None
    comment: str | None = None


class ApprovalStepTimelineRead(BaseModel):
    step_order: int
    step_name: str
    status: str
    tasks: list[ApprovalTaskTimelineRead]


class ApprovalProcessTimelineRead(BaseModel):
    id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None


class ApprovalTimelineRead(BaseModel):
    process: ApprovalProcessTimelineRead | None
    steps: list[ApprovalStepTimelineRead]
