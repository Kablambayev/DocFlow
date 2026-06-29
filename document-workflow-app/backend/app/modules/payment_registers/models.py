from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PaymentRegisterStatus(StrEnum):
    DRAFT = "Draft"
    READY_TO_SEND = "ReadyToSend"
    SENDING = "Sending"
    PARTIALLY_SENT = "PartiallySent"
    SENT = "Sent"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class PaymentRegister(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_registers"
    __table_args__ = (
        Index("ix_payment_registers_number", "number"),
        Index("ix_payment_registers_date", "date"),
        Index("ix_payment_registers_status", "status"),
        Index("ix_payment_registers_organization_id", "organization_id"),
        Index("ix_payment_registers_currency_id", "currency_id"),
        Index("ix_payment_registers_created_by", "created_by"),
        Index("ix_payment_registers_sent_at", "sent_at"),
    )

    number: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=PaymentRegisterStatus.DRAFT)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounting_organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    currency_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounting_currencies.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    sent_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PaymentRegisterRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_register_rows"
    __table_args__ = (
        UniqueConstraint("register_id", "document_id", name="uq_payment_register_rows_register_document"),
        Index("ix_payment_register_rows_register_id", "register_id"),
        Index("ix_payment_register_rows_document_id", "document_id"),
        Index("ix_payment_register_rows_row_number", "row_number"),
        Index("ix_payment_register_rows_export_status", "export_status"),
        Index("ix_payment_register_rows_export_id", "export_id"),
    )

    register_id: Mapped[UUID] = mapped_column(ForeignKey("payment_registers.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)

    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounting_organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    counterparty_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounting_counterparties.id", ondelete="SET NULL"),
        nullable=True,
    )
    contract_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounting_counterparty_contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    currency_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounting_currencies.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounting_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    expense_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounting_expense_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    export_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("payment_request_1c_exports.id", ondelete="SET NULL"),
        nullable=True,
    )
    one_c_payment_order_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    one_c_payment_order_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    one_c_payment_order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
