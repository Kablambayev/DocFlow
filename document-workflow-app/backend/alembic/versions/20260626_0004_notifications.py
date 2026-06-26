"""notifications

Revision ID: 20260626_0004
Revises: 20260626_0003
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260626_0004"
down_revision = "20260626_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["approval_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notifications_recipient_created_at", "notifications", ["recipient_id", "created_at"])
    op.create_index("idx_notifications_recipient_is_read", "notifications", ["recipient_id", "is_read"])
    op.create_index("idx_notifications_document_id", "notifications", ["document_id"])
    op.create_index("idx_notifications_task_id", "notifications", ["task_id"])
    op.alter_column("notifications", "payload", server_default=None)
    op.alter_column("notifications", "is_read", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_notifications_task_id", table_name="notifications")
    op.drop_index("idx_notifications_document_id", table_name="notifications")
    op.drop_index("idx_notifications_recipient_is_read", table_name="notifications")
    op.drop_index("idx_notifications_recipient_created_at", table_name="notifications")
    op.drop_table("notifications")
