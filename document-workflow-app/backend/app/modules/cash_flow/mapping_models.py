from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CashFlowMappingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cash_flow_mapping_rules"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "source_document_type_1c",
            "target_document_type_code",
            "priority",
            name="uq_cash_flow_mapping_rule_source_priority",
        ),
        Index("ix_cash_flow_mapping_rules_source_system", "source_system"),
        Index("ix_cash_flow_mapping_rules_source_document_type_1c", "source_document_type_1c"),
        Index("ix_cash_flow_mapping_rules_source_document_type_code", "source_document_type_code"),
        Index("ix_cash_flow_mapping_rules_direction", "cash_flow_direction"),
        Index("ix_cash_flow_mapping_rules_is_active", "is_active"),
        Index("ix_cash_flow_mapping_rules_priority", "priority"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="1C", nullable=False)
    source_document_type_1c: Mapped[str] = mapped_column(String(255), nullable=False)
    source_document_type_code: Mapped[str] = mapped_column(String(100), nullable=False)
    cash_flow_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    target_document_type_code: Mapped[str] = mapped_column(String(100), default="CashFlowAllocation", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    fields: Mapped[list["CashFlowMappingRuleField"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="CashFlowMappingRuleField.sort_order",
    )


class CashFlowMappingRuleField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cash_flow_mapping_rule_fields"
    __table_args__ = (
        Index("ix_cash_flow_mapping_rule_fields_rule_id", "rule_id"),
        Index("ix_cash_flow_mapping_rule_fields_target_field", "target_field"),
        Index("ix_cash_flow_mapping_rule_fields_mapping_type", "mapping_type"),
        Index("ix_cash_flow_mapping_rule_fields_sort_order", "sort_order"),
    )

    rule_id: Mapped[UUID] = mapped_column(ForeignKey("cash_flow_mapping_rules.id", ondelete="CASCADE"), nullable=False)
    target_field: Mapped[str] = mapped_column(String(100), nullable=False)
    mapping_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(255))
    constant_value: Mapped[dict | None] = mapped_column(JSONB)
    default_value: Mapped[dict | None] = mapped_column(JSONB)
    dictionary_type: Mapped[str | None] = mapped_column(String(100))
    lookup_by: Mapped[str | None] = mapped_column(String(50))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transform: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    rule: Mapped[CashFlowMappingRule] = relationship(back_populates="fields")
