from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_any_permission, require_permission
from app.db.session import get_db
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import DocumentCreate, DocumentRead, DocumentUpdate
from app.modules.documents.service import DocumentService
from app.modules.users.models import User

router = APIRouter(prefix="/documents", tags=["documents"])


def get_service(db: Session = Depends(get_db)) -> DocumentService:
	return DocumentService(DocumentRepository(db))


@router.get("", response_model=list[DocumentRead])
def list_documents(
	current_user: User = Depends(require_any_permission("document.read", "integration_1c.payment_request.send")),
	service: DocumentService = Depends(get_service),
) -> list[DocumentRead]:
	return service.list_documents(current_user.id)


@router.post("", response_model=DocumentRead)
def create_document(
	payload: DocumentCreate,
	_: User = Depends(require_permission("document.create")),
	service: DocumentService = Depends(get_service),
) -> DocumentRead:
	return service.create_document(payload)


@router.get("/{id}", response_model=DocumentRead)
def get_document(
	id: UUID,
	current_user: User = Depends(require_any_permission("document.read", "integration_1c.payment_request.send")),
	service: DocumentService = Depends(get_service),
) -> DocumentRead:
	return service.get_document(id, current_user.id)


@router.put("/{id}", response_model=DocumentRead)
def update_document(
	id: UUID,
	payload: DocumentUpdate,
	current_user: User = Depends(require_permission("document.update")),
	service: DocumentService = Depends(get_service),
) -> DocumentRead:
	return service.update_document(id, payload, current_user.id)


@router.post("/{id}/submit", response_model=DocumentRead)
def submit_document(
	id: UUID,
	current_user: User = Depends(require_permission("document.submit")),
	service: DocumentService = Depends(get_service),
) -> DocumentRead:
	return service.submit_document(id, current_user.id)


@router.post("/{id}/withdraw", response_model=DocumentRead)
def withdraw_document(
	id: UUID,
	current_user: User = Depends(require_permission("document.withdraw")),
	service: DocumentService = Depends(get_service),
) -> DocumentRead:
	return service.withdraw_document(id, current_user.id)

