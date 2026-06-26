from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.db.session import get_db
from app.modules.document_types.repository import DocumentTypeRepository
from app.modules.document_types.schemas import (
    DocumentTypeCreate,
    DocumentTypeRead,
    DocumentTypeUpdate,
    DocumentTypeVersionCreate,
    DocumentTypeVersionRead,
)
from app.modules.document_types.service import DocumentTypeService
from app.modules.users.models import User

router = APIRouter(prefix="/document-types", tags=["document-types"])


def get_service(db: Session = Depends(get_db)) -> DocumentTypeService:
    return DocumentTypeService(DocumentTypeRepository(db))


@router.get("", response_model=list[DocumentTypeRead])
def list_document_types(
    _: User = Depends(require_permission("document_type.read")),
    service: DocumentTypeService = Depends(get_service),
) -> list[DocumentTypeRead]:
    return service.list_document_types()


@router.get("/active", response_model=list[DocumentTypeRead])
def list_active_document_types(
    _: User = Depends(require_permission("document_type.read")),
    service: DocumentTypeService = Depends(get_service),
) -> list[DocumentTypeRead]:
    return service.list_active_document_types()


@router.post("", response_model=DocumentTypeRead)
def create_document_type(
    payload: DocumentTypeCreate,
    _: User = Depends(require_permission("document_type.create")),
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeRead:
    return service.create_document_type(payload)


@router.get("/{id}", response_model=DocumentTypeRead)
def get_document_type(
    id: UUID,
    _: User = Depends(require_permission("document_type.read")),
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeRead:
    return service.get_document_type(id)


@router.put("/{id}", response_model=DocumentTypeRead)
def update_document_type(
    id: UUID,
    payload: DocumentTypeUpdate,
    _: User = Depends(require_permission("document_type.update")),
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeRead:
    return service.update_document_type(id, payload)


@router.get("/{id}/published-version", response_model=DocumentTypeVersionRead)
def get_published_document_type_version(
    id: UUID,
    _: User = Depends(require_permission("document_type.read")),
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.get_published_version(id)


@router.get("/{id}/versions", response_model=list[DocumentTypeVersionRead])
def list_document_type_versions(
    id: UUID,
    _: User = Depends(require_permission("document_type.read")),
    service: DocumentTypeService = Depends(get_service),
) -> list[DocumentTypeVersionRead]:
    return service.list_versions(id)


@router.post("/{id}/versions", response_model=DocumentTypeVersionRead)
def create_document_type_version(
    id: UUID,
    payload: DocumentTypeVersionCreate,
    _: User = Depends(require_permission("document_type.update")),
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.create_document_type_version(id, payload)

