from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class VersionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DocumentType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_types"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    versions: Mapped[list["DocumentTypeVersion"]] = relationship(back_populates="document_type")


class DocumentTypeVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_type_versions"
    __table_args__ = (UniqueConstraint("document_type_id", "version_number", name="uq_document_type_version_number"),)

    document_type_id: Mapped[UUID] = mapped_column(ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=VersionStatus.DRAFT, nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document_type: Mapped[DocumentType] = relationship(back_populates="versions")
    fields: Mapped[list["DocumentTypeField"]] = relationship(back_populates="document_type_version")


class DocumentTypeField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_type_fields"

    document_type_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_type_versions.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    section_code: Mapped[str | None] = mapped_column(String(100))
    settings_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    validation_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    document_type_version: Mapped[DocumentTypeVersion] = relationship(back_populates="fields")
