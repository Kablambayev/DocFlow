"""add payment request 1c exports

Revision ID: 20260629_0007
Revises: 20260626_0006
Create Date: 2026-06-29 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260629_0007"
down_revision = "20260626_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_request_1c_exports",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("one_c_payment_order_external_id", sa.String(length=255), nullable=True),
        sa.Column("one_c_payment_order_number", sa.String(length=100), nullable=True),
        sa.Column("one_c_payment_order_date", sa.Date(), nullable=True),
        sa.Column("one_c_payment_order_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("one_c_payment_order_currency_code", sa.String(length=20), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sent_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_payment_request_1c_exports_document_id"),
    )
    op.create_index(
        "idx_payment_request_1c_exports_document_id",
        "payment_request_1c_exports",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "idx_payment_request_1c_exports_status",
        "payment_request_1c_exports",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_payment_request_1c_exports_payment_order_external_id",
        "payment_request_1c_exports",
        ["one_c_payment_order_external_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_payment_request_1c_exports_payment_order_external_id",
        table_name="payment_request_1c_exports",
    )
    op.drop_index("idx_payment_request_1c_exports_status", table_name="payment_request_1c_exports")
    op.drop_index("idx_payment_request_1c_exports_document_id", table_name="payment_request_1c_exports")
    op.drop_table("payment_request_1c_exports")