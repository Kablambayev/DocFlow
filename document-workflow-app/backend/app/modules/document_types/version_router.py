from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.document_types.repository import DocumentTypeRepository
from app.modules.document_types.schemas import (
    DocumentTypeFieldRequest,
    DocumentTypeSectionRequest,
    DocumentTypeVersionRead,
    DocumentTypeVersionUpdate,
    SchemaValidationResult,
)
from app.modules.document_types.service import DocumentTypeService

router = APIRouter(prefix="/document-type-versions", tags=["document-types"])


def get_service(db: Session = Depends(get_db)) -> DocumentTypeService:
    return DocumentTypeService(DocumentTypeRepository(db))


@router.post("/{id}/publish", response_model=DocumentTypeVersionRead)
def publish_document_type_version(
    id: UUID,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.publish_version(id)


@router.get("/{id}", response_model=DocumentTypeVersionRead)
def get_document_type_version(
    id: UUID,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.get_version(id)


@router.put("/{id}", response_model=DocumentTypeVersionRead)
def update_document_type_version(
    id: UUID,
    payload: DocumentTypeVersionUpdate,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.update_version(id, payload)


@router.post("/{id}/sections", response_model=DocumentTypeVersionRead)
def add_document_type_section(
    id: UUID,
    payload: DocumentTypeSectionRequest,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.add_section(id, payload)


@router.put("/{id}/sections/{section_code}", response_model=DocumentTypeVersionRead)
def update_document_type_section(
    id: UUID,
    section_code: str,
    payload: DocumentTypeSectionRequest,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.update_section(id, section_code, payload)


@router.delete("/{id}/sections/{section_code}", response_model=DocumentTypeVersionRead)
def delete_document_type_section(
    id: UUID,
    section_code: str,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.delete_section(id, section_code)


@router.post("/{id}/fields", response_model=DocumentTypeVersionRead)
def add_document_type_field(
    id: UUID,
    payload: DocumentTypeFieldRequest,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.add_field(id, payload)


@router.put("/{id}/fields/{field_code}", response_model=DocumentTypeVersionRead)
def update_document_type_field(
    id: UUID,
    field_code: str,
    payload: DocumentTypeFieldRequest,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.update_field(id, field_code, payload)


@router.delete("/{id}/fields/{field_code}", response_model=DocumentTypeVersionRead)
def delete_document_type_field(
    id: UUID,
    field_code: str,
    service: DocumentTypeService = Depends(get_service),
) -> DocumentTypeVersionRead:
    return service.delete_field(id, field_code)


@router.post("/{id}/validate-schema", response_model=SchemaValidationResult)
def validate_document_type_schema(
    id: UUID,
    service: DocumentTypeService = Depends(get_service),
) -> SchemaValidationResult:
    return service.validate_schema(id)


@router.get("", response_model=list[DocumentTypeVersionRead])
def list_document_type_versions(
    document_type_id: UUID,
    service: DocumentTypeService = Depends(get_service),
) -> list[DocumentTypeVersionRead]:
    return service.list_versions(document_type_id)
