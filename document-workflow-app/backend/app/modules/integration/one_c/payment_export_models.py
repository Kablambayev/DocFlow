from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PaymentRequest1CExportStatus(StrEnum):
    PENDING = "Pending"
    SENT = "Sent"
    CREATED_IN_1C = "CreatedIn1C"
    ALREADY_EXISTS_IN_1C = "AlreadyExistsIn1C"
    FAILED = "Failed"


class PaymentRequest1CExport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_request_1c_exports"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_payment_request_1c_exports_document_id"),
        Index("idx_payment_request_1c_exports_document_id", "document_id"),
        Index("idx_payment_request_1c_exports_status", "status"),
        Index(
            "idx_payment_request_1c_exports_payment_order_external_id",
            "one_c_payment_order_external_id",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=PaymentRequest1CExportStatus.PENDING)

    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    sent_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    response_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    one_c_payment_order_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    one_c_payment_order_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    one_c_payment_order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    one_c_payment_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    one_c_payment_order_currency_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)