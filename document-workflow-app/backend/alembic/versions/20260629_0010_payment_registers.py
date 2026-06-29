"""payment registers

Revision ID: 20260629_0010
Revises: 20260629_0009
Create Date: 2026-06-29 16:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260629_0010"
down_revision = "20260629_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_registers",
        sa.Column("number", sa.String(length=100), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sent_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sent_rows_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_rows_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["currency_id"], ["accounting_currencies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["accounting_organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sent_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_registers_number", "payment_registers", ["number"], unique=False)
    op.create_index("ix_payment_registers_date", "payment_registers", ["date"], unique=False)
    op.create_index("ix_payment_registers_status", "payment_registers", ["status"], unique=False)
    op.create_index("ix_payment_registers_organization_id", "payment_registers", ["organization_id"], unique=False)
    op.create_index("ix_payment_registers_currency_id", "payment_registers", ["currency_id"], unique=False)
    op.create_index("ix_payment_registers_created_by", "payment_registers", ["created_by"], unique=False)
    op.create_index("ix_payment_registers_sent_at", "payment_registers", ["sent_at"], unique=False)

    op.create_table(
        "payment_register_rows",
        sa.Column("register_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expense_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_purpose", sa.Text(), nullable=True),
        sa.Column("export_status", sa.String(length=50), nullable=True),
        sa.Column("export_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("one_c_payment_order_external_id", sa.String(length=255), nullable=True),
        sa.Column("one_c_payment_order_number", sa.String(length=100), nullable=True),
        sa.Column("one_c_payment_order_date", sa.Date(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["accounting_counterparty_contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["counterparty_id"], ["accounting_counterparties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["currency_id"], ["accounting_currencies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expense_item_id"], ["accounting_expense_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["export_id"], ["payment_request_1c_exports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["accounting_organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["accounting_projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["register_id"], ["payment_registers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("register_id", "document_id", name="uq_payment_register_rows_register_document"),
    )
    op.create_index("ix_payment_register_rows_register_id", "payment_register_rows", ["register_id"], unique=False)
    op.create_index("ix_payment_register_rows_document_id", "payment_register_rows", ["document_id"], unique=False)
    op.create_index("ix_payment_register_rows_row_number", "payment_register_rows", ["row_number"], unique=False)
    op.create_index("ix_payment_register_rows_export_status", "payment_register_rows", ["export_status"], unique=False)
    op.create_index("ix_payment_register_rows_export_id", "payment_register_rows", ["export_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payment_register_rows_export_id", table_name="payment_register_rows")
    op.drop_index("ix_payment_register_rows_export_status", table_name="payment_register_rows")
    op.drop_index("ix_payment_register_rows_row_number", table_name="payment_register_rows")
    op.drop_index("ix_payment_register_rows_document_id", table_name="payment_register_rows")
    op.drop_index("ix_payment_register_rows_register_id", table_name="payment_register_rows")
    op.drop_table("payment_register_rows")

    op.drop_index("ix_payment_registers_sent_at", table_name="payment_registers")
    op.drop_index("ix_payment_registers_created_by", table_name="payment_registers")
    op.drop_index("ix_payment_registers_currency_id", table_name="payment_registers")
    op.drop_index("ix_payment_registers_organization_id", table_name="payment_registers")
    op.drop_index("ix_payment_registers_status", table_name="payment_registers")
    op.drop_index("ix_payment_registers_date", table_name="payment_registers")
    op.drop_index("ix_payment_registers_number", table_name="payment_registers")
    op.drop_table("payment_registers")
