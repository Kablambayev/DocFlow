from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class IntegrationOperationLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_operation_logs"
    __table_args__ = (
        Index("idx_integration_logs_created_at", "created_at"),
        Index("idx_integration_logs_direction", "direction"),
        Index("idx_integration_logs_operation_type", "operation_type"),
        Index("idx_integration_logs_status", "status"),
        Index("idx_integration_logs_document_id", "document_id"),
        Index("idx_integration_logs_correlation_id", "correlation_id"),
        Index("idx_integration_logs_idempotency_key", "idempotency_key"),
    )

    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    integration_system: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'1C'"))
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    document_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    initiated_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    request_url: Mapped[str | None] = mapped_column(Text)
    request_method: Mapped[str | None] = mapped_column(String(20))
    request_headers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    response_status_code: Mapped[int | None] = mapped_column(Integer)
    response_headers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    response_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    error_details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    duration_ms: Mapped[int | None] = mapped_column(Integer)
    correlation_id: Mapped[str | None] = mapped_column(String(200))
    idempotency_key: Mapped[str | None] = mapped_column(String(200))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
