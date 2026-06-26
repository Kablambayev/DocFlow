"""accounting dictionaries

Revision ID: 20260626_0005
Revises: 20260626_0004
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260626_0005"
down_revision = "20260626_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_system", sa.String(length=32), nullable=False, server_default=sa.text("'1C'")),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "external_id", name="uq_acc_org_source_external"),
    )

    op.create_table(
        "accounting_counterparties",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=500), nullable=True),
        sa.Column("bin_iin", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_system", sa.String(length=32), nullable=False, server_default=sa.text("'1C'")),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "external_id", name="uq_acc_counterparty_source_external"),
    )

    op.create_table(
        "accounting_currencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=500), nullable=True),
        sa.Column("numeric_code", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_system", sa.String(length=32), nullable=False, server_default=sa.text("'1C'")),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "external_id", name="uq_acc_currency_source_external"),
        sa.UniqueConstraint("code", name="uq_acc_currency_code"),
    )

    op.create_table(
        "accounting_expense_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_system", sa.String(length=32), nullable=False, server_default=sa.text("'1C'")),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "external_id", name="uq_acc_expense_source_external"),
    )

    op.create_table(
        "accounting_cash_flow_operation_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "accounting_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "accounting_counterparty_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("number", sa.String(length=100), nullable=True),
        sa.Column("contract_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_system", sa.String(length=32), nullable=False, server_default=sa.text("'1C'")),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["counterparty_id"], ["accounting_counterparties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["currency_id"], ["accounting_currencies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["accounting_organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "external_id", name="uq_acc_contract_source_external"),
    )

    op.create_index("idx_accounting_contracts_organization_id", "accounting_counterparty_contracts", ["organization_id"])
    op.create_index("idx_accounting_contracts_counterparty_id", "accounting_counterparty_contracts", ["counterparty_id"])
    op.create_index("idx_accounting_contracts_org_counterparty", "accounting_counterparty_contracts", ["organization_id", "counterparty_id"])

    for table_name in [
        "accounting_organizations",
        "accounting_counterparties",
        "accounting_currencies",
        "accounting_expense_items",
        "accounting_counterparty_contracts",
        "accounting_cash_flow_operation_types",
        "accounting_projects",
    ]:
        op.alter_column(table_name, "is_active", server_default=None)
        op.alter_column(table_name, "updated_at", server_default=None)

    for table_name in [
        "accounting_organizations",
        "accounting_counterparties",
        "accounting_currencies",
        "accounting_expense_items",
        "accounting_counterparty_contracts",
    ]:
        op.alter_column(table_name, "source_system", server_default=None)
        op.alter_column(table_name, "raw_data", server_default=None)

    op.alter_column("accounting_cash_flow_operation_types", "sort_order", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_accounting_contracts_org_counterparty", table_name="accounting_counterparty_contracts")
    op.drop_index("idx_accounting_contracts_counterparty_id", table_name="accounting_counterparty_contracts")
    op.drop_index("idx_accounting_contracts_organization_id", table_name="accounting_counterparty_contracts")

    op.drop_table("accounting_counterparty_contracts")
    op.drop_table("accounting_projects")
    op.drop_table("accounting_cash_flow_operation_types")
    op.drop_table("accounting_expense_items")
    op.drop_table("accounting_currencies")
    op.drop_table("accounting_counterparties")
    op.drop_table("accounting_organizations")
