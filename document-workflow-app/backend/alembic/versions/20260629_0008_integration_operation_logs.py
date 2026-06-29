"""integration operation logs

Revision ID: 20260629_0008
Revises: 20260629_0007
Create Date: 2026-06-29 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260629_0008"
down_revision = "20260629_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_operation_logs",
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("integration_system", sa.String(length=50), server_default=sa.text("'1C'"), nullable=False),
        sa.Column("operation_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("initiated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_url", sa.Text(), nullable=True),
        sa.Column("request_method", sa.String(length=20), nullable=True),
        sa.Column("request_headers", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_headers", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("correlation_id", sa.String(length=200), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_integration_logs_created_at", "integration_operation_logs", ["created_at"], unique=False)
    op.create_index("idx_integration_logs_direction", "integration_operation_logs", ["direction"], unique=False)
    op.create_index("idx_integration_logs_operation_type", "integration_operation_logs", ["operation_type"], unique=False)
    op.create_index("idx_integration_logs_status", "integration_operation_logs", ["status"], unique=False)
    op.create_index("idx_integration_logs_document_id", "integration_operation_logs", ["document_id"], unique=False)
    op.create_index("idx_integration_logs_correlation_id", "integration_operation_logs", ["correlation_id"], unique=False)
    op.create_index("idx_integration_logs_idempotency_key", "integration_operation_logs", ["idempotency_key"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_integration_logs_idempotency_key", table_name="integration_operation_logs")
    op.drop_index("idx_integration_logs_correlation_id", table_name="integration_operation_logs")
    op.drop_index("idx_integration_logs_document_id", table_name="integration_operation_logs")
    op.drop_index("idx_integration_logs_status", table_name="integration_operation_logs")
    op.drop_index("idx_integration_logs_operation_type", table_name="integration_operation_logs")
    op.drop_index("idx_integration_logs_direction", table_name="integration_operation_logs")
    op.drop_index("idx_integration_logs_created_at", table_name="integration_operation_logs")
    op.drop_table("integration_operation_logs")
