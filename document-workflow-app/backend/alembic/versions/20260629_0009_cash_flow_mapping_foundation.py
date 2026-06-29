"""cash flow mapping foundation

Revision ID: 20260629_0009
Revises: 20260629_0008
Create Date: 2026-06-29 14:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260629_0009"
down_revision = "20260629_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_cash_flow_items",
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("direction", sa.String(length=20), server_default=sa.text("'Both'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("source_system", sa.String(length=50), server_default=sa.text("'1C'"), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "external_id", name="uq_acc_cash_flow_item_source_external"),
    )
    op.create_index("ix_acc_cash_flow_items_code", "accounting_cash_flow_items", ["code"], unique=False)
    op.create_index("ix_acc_cash_flow_items_direction", "accounting_cash_flow_items", ["direction"], unique=False)
    op.create_index("ix_acc_cash_flow_items_is_active", "accounting_cash_flow_items", ["is_active"], unique=False)

    op.create_table(
        "cash_flow_mapping_rules",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_system", sa.String(length=50), server_default=sa.text("'1C'"), nullable=False),
        sa.Column("source_document_type_1c", sa.String(length=255), nullable=False),
        sa.Column("source_document_type_code", sa.String(length=100), nullable=False),
        sa.Column("cash_flow_direction", sa.String(length=20), nullable=False),
        sa.Column("target_document_type_code", sa.String(length=100), server_default=sa.text("'CashFlowAllocation'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_system",
            "source_document_type_1c",
            "target_document_type_code",
            "priority",
            name="uq_cash_flow_mapping_rule_source_priority",
        ),
    )
    op.create_index("ix_cash_flow_mapping_rules_source_system", "cash_flow_mapping_rules", ["source_system"], unique=False)
    op.create_index(
        "ix_cash_flow_mapping_rules_source_document_type_1c",
        "cash_flow_mapping_rules",
        ["source_document_type_1c"],
        unique=False,
    )
    op.create_index(
        "ix_cash_flow_mapping_rules_source_document_type_code",
        "cash_flow_mapping_rules",
        ["source_document_type_code"],
        unique=False,
    )
    op.create_index("ix_cash_flow_mapping_rules_direction", "cash_flow_mapping_rules", ["cash_flow_direction"], unique=False)
    op.create_index("ix_cash_flow_mapping_rules_is_active", "cash_flow_mapping_rules", ["is_active"], unique=False)
    op.create_index("ix_cash_flow_mapping_rules_priority", "cash_flow_mapping_rules", ["priority"], unique=False)

    op.create_table(
        "cash_flow_mapping_rule_fields",
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_field", sa.String(length=100), nullable=False),
        sa.Column("mapping_type", sa.String(length=50), nullable=False),
        sa.Column("source_path", sa.String(length=255), nullable=True),
        sa.Column("constant_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("default_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dictionary_type", sa.String(length=100), nullable=True),
        sa.Column("lookup_by", sa.String(length=50), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("transform", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["cash_flow_mapping_rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_flow_mapping_rule_fields_rule_id", "cash_flow_mapping_rule_fields", ["rule_id"], unique=False)
    op.create_index(
        "ix_cash_flow_mapping_rule_fields_target_field",
        "cash_flow_mapping_rule_fields",
        ["target_field"],
        unique=False,
    )
    op.create_index(
        "ix_cash_flow_mapping_rule_fields_mapping_type",
        "cash_flow_mapping_rule_fields",
        ["mapping_type"],
        unique=False,
    )
    op.create_index(
        "ix_cash_flow_mapping_rule_fields_sort_order",
        "cash_flow_mapping_rule_fields",
        ["sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cash_flow_mapping_rule_fields_sort_order", table_name="cash_flow_mapping_rule_fields")
    op.drop_index("ix_cash_flow_mapping_rule_fields_mapping_type", table_name="cash_flow_mapping_rule_fields")
    op.drop_index("ix_cash_flow_mapping_rule_fields_target_field", table_name="cash_flow_mapping_rule_fields")
    op.drop_index("ix_cash_flow_mapping_rule_fields_rule_id", table_name="cash_flow_mapping_rule_fields")
    op.drop_table("cash_flow_mapping_rule_fields")

    op.drop_index("ix_cash_flow_mapping_rules_priority", table_name="cash_flow_mapping_rules")
    op.drop_index("ix_cash_flow_mapping_rules_is_active", table_name="cash_flow_mapping_rules")
    op.drop_index("ix_cash_flow_mapping_rules_direction", table_name="cash_flow_mapping_rules")
    op.drop_index("ix_cash_flow_mapping_rules_source_document_type_code", table_name="cash_flow_mapping_rules")
    op.drop_index("ix_cash_flow_mapping_rules_source_document_type_1c", table_name="cash_flow_mapping_rules")
    op.drop_index("ix_cash_flow_mapping_rules_source_system", table_name="cash_flow_mapping_rules")
    op.drop_table("cash_flow_mapping_rules")

    op.drop_index("ix_acc_cash_flow_items_is_active", table_name="accounting_cash_flow_items")
    op.drop_index("ix_acc_cash_flow_items_direction", table_name="accounting_cash_flow_items")
    op.drop_index("ix_acc_cash_flow_items_code", table_name="accounting_cash_flow_items")
    op.drop_table("accounting_cash_flow_items")
