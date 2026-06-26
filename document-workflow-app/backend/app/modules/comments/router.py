from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.comments.repository import CommentRepository
from app.modules.comments.schemas import (
    ApprovalTimelineRead,
    DeleteCommentResponse,
    DocumentCommentCreate,
    DocumentCommentRead,
    DocumentCommentUpdate,
    TimelineItem,
)
from app.modules.comments.service import CommentService
from app.modules.users.models import User

router = APIRouter(tags=["comments"])


def get_service(db: Session = Depends(get_db)) -> CommentService:
    return CommentService(CommentRepository(db))


@router.get("/documents/{document_id}/comments", response_model=list[DocumentCommentRead])
def list_comments(document_id: UUID, current_user: User = Depends(get_current_user), service: CommentService = Depends(get_service)):
    return service.list_comments(document_id, current_user)


@router.post("/documents/{document_id}/comments", response_model=DocumentCommentRead)
def create_comment(document_id: UUID, payload: DocumentCommentCreate, current_user: User = Depends(get_current_user), service: CommentService = Depends(get_service)):
    return service.create_comment(document_id, payload, current_user)


@router.put("/comments/{comment_id}", response_model=DocumentCommentRead)
def update_comment(comment_id: UUID, payload: DocumentCommentUpdate, current_user: User = Depends(get_current_user), service: CommentService = Depends(get_service)):
    return service.update_comment(comment_id, payload, current_user)


@router.delete("/comments/{comment_id}", response_model=DeleteCommentResponse)
def delete_comment(comment_id: UUID, current_user: User = Depends(get_current_user), service: CommentService = Depends(get_service)):
    service.delete_comment(comment_id, current_user)
    return DeleteCommentResponse()


@router.get("/documents/{document_id}/timeline", response_model=list[TimelineItem])
def get_document_timeline(document_id: UUID, current_user: User = Depends(get_current_user), service: CommentService = Depends(get_service)):
    return service.get_document_timeline(document_id, current_user)


@router.get("/documents/{document_id}/approval-timeline", response_model=ApprovalTimelineRead)
def get_approval_timeline(document_id: UUID, current_user: User = Depends(get_current_user), service: CommentService = Depends(get_service)):
    return service.get_approval_timeline(document_id, current_user)
