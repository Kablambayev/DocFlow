"""document file soft delete fields

Revision ID: 20260626_0002
Revises: 20260626_0001
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260626_0002"
down_revision = "20260626_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_files",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "document_files",
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "document_files",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_document_files_deleted_by_users",
        "document_files",
        "users",
        ["deleted_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column("document_files", "is_deleted", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_document_files_deleted_by_users", "document_files", type_="foreignkey")
    op.drop_column("document_files", "deleted_at")
    op.drop_column("document_files", "deleted_by")
    op.drop_column("document_files", "is_deleted")
