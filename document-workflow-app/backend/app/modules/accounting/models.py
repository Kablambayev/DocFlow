from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AccountingOrganization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_organizations"
    __table_args__ = (UniqueConstraint("source_system", "external_id", name="uq_acc_org_source_external"),)

    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="1C", nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountingCounterparty(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_counterparties"
    __table_args__ = (UniqueConstraint("source_system", "external_id", name="uq_acc_counterparty_source_external"),)

    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text)
    bin_iin: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="1C", nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountingCurrency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_currencies"
    __table_args__ = (
        UniqueConstraint("source_system", "external_id", name="uq_acc_currency_source_external"),
        UniqueConstraint("code", name="uq_acc_currency_code"),
    )

    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text)
    numeric_code: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="1C", nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountingExpenseItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_expense_items"
    __table_args__ = (UniqueConstraint("source_system", "external_id", name="uq_acc_expense_source_external"),)

    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="1C", nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountingCounterpartyContract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_counterparty_contracts"
    __table_args__ = (
        UniqueConstraint("source_system", "external_id", name="uq_acc_contract_source_external"),
        Index("idx_accounting_contracts_organization_id", "organization_id"),
        Index("idx_accounting_contracts_counterparty_id", "counterparty_id"),
        Index("idx_accounting_contracts_org_counterparty", "organization_id", "counterparty_id"),
    )

    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("accounting_organizations.id", ondelete="RESTRICT"), nullable=False)
    counterparty_id: Mapped[UUID] = mapped_column(ForeignKey("accounting_counterparties.id", ondelete="RESTRICT"), nullable=False)
    currency_id: Mapped[UUID | None] = mapped_column(ForeignKey("accounting_currencies.id", ondelete="RESTRICT"), nullable=True)
    code: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    number: Mapped[str | None] = mapped_column(String(100))
    contract_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="1C", nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountingCashFlowOperationType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_cash_flow_operation_types"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)


class AccountingCashFlowItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_cash_flow_items"
    __table_args__ = (
        UniqueConstraint("source_system", "external_id", name="uq_acc_cash_flow_item_source_external"),
        Index("ix_acc_cash_flow_items_code", "code"),
        Index("ix_acc_cash_flow_items_direction", "direction"),
        Index("ix_acc_cash_flow_items_is_active", "is_active"),
    )

    external_id: Mapped[str | None] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(String(20), default="Both", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="1C", nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountingProject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_projects"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    responsible_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
