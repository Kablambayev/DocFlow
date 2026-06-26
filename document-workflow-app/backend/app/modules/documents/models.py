from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentApprovalStatus(StrEnum):
    DRAFT = "Draft"
    ON_APPROVAL = "OnApproval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    RETURNED = "Returned"
    WITHDRAWN = "Withdrawn"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_document_type_id", "document_type_id"),
        Index("ix_documents_author_id", "author_id"),
        Index("ix_documents_approval_status", "approval_status"),
        Index("ix_documents_document_date", "document_date"),
        Index("ix_documents_data_json", "data_json", postgresql_using="gin"),
    )

    document_type_id: Mapped[UUID] = mapped_column(ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False)
    document_type_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_type_versions.id", ondelete="RESTRICT"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(100), nullable=False)
    document_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(20), nullable=False, default=DocumentApprovalStatus.DRAFT)
    business_status: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    data_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
