from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.session import get_db
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import DocumentCreate, DocumentRead, DocumentUpdate
from app.modules.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_service(db: Session = Depends(get_db)) -> DocumentService:
	return DocumentService(DocumentRepository(db))


def get_user_id_header(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> UUID:
	if x_user_id is None:
		raise AppError("X-User-Id header is required", code="UNAUTHORIZED", status_code=401)
	return UUID(x_user_id)


@router.get("", response_model=list[DocumentRead])
def list_documents(service: DocumentService = Depends(get_service)) -> list[DocumentRead]:
	return service.list_documents()


@router.post("", response_model=DocumentRead)
def create_document(payload: DocumentCreate, service: DocumentService = Depends(get_service)) -> DocumentRead:
	return service.create_document(payload)


@router.get("/{id}", response_model=DocumentRead)
def get_document(id: UUID, service: DocumentService = Depends(get_service)) -> DocumentRead:
	return service.get_document(id)


@router.put("/{id}", response_model=DocumentRead)
def update_document(id: UUID, payload: DocumentUpdate, service: DocumentService = Depends(get_service)) -> DocumentRead:
	return service.update_document(id, payload)


@router.post("/{id}/submit", response_model=DocumentRead)
def submit_document(
	id: UUID,
	user_id: UUID = Depends(get_user_id_header),
	service: DocumentService = Depends(get_service),
) -> DocumentRead:
	return service.submit_document(id, user_id)


@router.post("/{id}/withdraw", response_model=DocumentRead)
def withdraw_document(
	id: UUID,
	user_id: UUID = Depends(get_user_id_header),
	service: DocumentService = Depends(get_service),
) -> DocumentRead:
	return service.withdraw_document(id, user_id)

