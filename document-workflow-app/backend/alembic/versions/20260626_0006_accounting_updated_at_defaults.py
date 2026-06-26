"""restore accounting updated_at defaults

Revision ID: 20260626_0006
Revises: 20260626_0005
Create Date: 2026-06-26 00:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260626_0006"
down_revision = "20260626_0005"
branch_labels = None
depends_on = None


ACCOUNTING_TABLES = [
    "accounting_organizations",
    "accounting_counterparties",
    "accounting_currencies",
    "accounting_expense_items",
    "accounting_counterparty_contracts",
    "accounting_cash_flow_operation_types",
    "accounting_projects",
]


def upgrade() -> None:
    for table_name in ACCOUNTING_TABLES:
        op.alter_column(table_name, "updated_at", server_default=sa.func.now())


def downgrade() -> None:
    for table_name in ACCOUNTING_TABLES:
        op.alter_column(table_name, "updated_at", server_default=None)
