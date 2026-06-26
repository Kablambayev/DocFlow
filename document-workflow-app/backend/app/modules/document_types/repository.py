from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.document_types.schemas import DocumentTypeCreate, DocumentTypeUpdate, DocumentTypeVersionCreate


class DocumentTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[DocumentType]:
        return list(self.db.scalars(select(DocumentType).order_by(DocumentType.created_at.desc())))

    def list_active_with_published_version(self) -> list[DocumentType]:
        stmt = (
            select(DocumentType)
            .join(DocumentTypeVersion, DocumentTypeVersion.document_type_id == DocumentType.id)
            .where(DocumentType.is_active.is_(True), DocumentTypeVersion.status == VersionStatus.PUBLISHED)
            .distinct()
            .order_by(DocumentType.name.asc())
        )
        return list(self.db.scalars(stmt))

    def get(self, item_id: UUID) -> DocumentType | None:
        return self.db.get(DocumentType, item_id)

    def get_by_code(self, code: str) -> DocumentType | None:
        return self.db.scalar(select(DocumentType).where(DocumentType.code == code))

    def create(self, payload: DocumentTypeCreate) -> DocumentType:
        item = DocumentType(**payload.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, item: DocumentType, payload: DocumentTypeUpdate) -> DocumentType:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_version(self, document_type_id: UUID, payload: DocumentTypeVersionCreate) -> DocumentTypeVersion:
        last_version = self.db.scalar(
            select(func.max(DocumentTypeVersion.version_number)).where(DocumentTypeVersion.document_type_id == document_type_id)
        )
        new_version = DocumentTypeVersion(
            document_type_id=document_type_id,
            version_number=(last_version or 0) + 1,
            status=VersionStatus.DRAFT,
            schema_json=payload.schema_payload,
        )
        self.db.add(new_version)
        self.db.commit()
        self.db.refresh(new_version)
        return new_version

    def get_version(self, version_id: UUID) -> DocumentTypeVersion | None:
        return self.db.get(DocumentTypeVersion, version_id)

    def get_latest_published_version(self, document_type_id: UUID) -> DocumentTypeVersion | None:
        return self.db.scalar(
            select(DocumentTypeVersion)
            .where(
                DocumentTypeVersion.document_type_id == document_type_id,
                DocumentTypeVersion.status == VersionStatus.PUBLISHED,
            )
            .order_by(DocumentTypeVersion.version_number.desc())
        )

    def list_versions_by_document_type(self, document_type_id: UUID) -> list[DocumentTypeVersion]:
        return list(
            self.db.scalars(
                select(DocumentTypeVersion)
                .where(DocumentTypeVersion.document_type_id == document_type_id)
                .order_by(DocumentTypeVersion.version_number.desc())
            )
        )

    def publish_version(self, version: DocumentTypeVersion) -> DocumentTypeVersion:
        published_versions = list(
            self.db.scalars(
                select(DocumentTypeVersion).where(
                    DocumentTypeVersion.document_type_id == version.document_type_id,
                    DocumentTypeVersion.status == VersionStatus.PUBLISHED,
                )
            )
        )
        for previous in published_versions:
            previous.status = VersionStatus.ARCHIVED

        version.status = VersionStatus.PUBLISHED
        version.published_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(version)
        return version

    def update_version_schema(self, version: DocumentTypeVersion, schema_json: dict) -> DocumentTypeVersion:
        version.schema_json = schema_json
        self.db.commit()
        self.db.refresh(version)
        return version
