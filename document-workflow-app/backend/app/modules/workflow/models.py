from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProcessStatus(StrEnum):
    RUNNING = "Running"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"


class TaskStatus(StrEnum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    SKIPPED = "Skipped"


class DecisionType(StrEnum):
    APPROVE = "Approve"
    REJECT = "Reject"
    RETURN = "Return"


class ApprovalRoute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_routes"

    document_type_id: Mapped[UUID] = mapped_column(ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ApprovalRouteVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_route_versions"

    route_id: Mapped[UUID] = mapped_column(ForeignKey("approval_routes.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    route_schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalMatrixRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_matrix_rules"
    __table_args__ = (
        Index("ix_approval_matrix_rules_doc_type_priority", "document_type_id", "priority"),
        Index("ix_approval_matrix_rules_condition_json", "condition_json", postgresql_using="gin"),
    )

    document_type_id: Mapped[UUID] = mapped_column(ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    condition_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    route_id: Mapped[UUID] = mapped_column(ForeignKey("approval_routes.id", ondelete="RESTRICT"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ApprovalProcess(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "approval_processes"

    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    route_version_id: Mapped[UUID] = mapped_column(ForeignKey("approval_route_versions.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_step_order: Mapped[int | None] = mapped_column(Integer)
    started_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalTask(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "approval_tasks"
    __table_args__ = (
        Index(
            "ix_approval_tasks_pending_approver_created",
            "approver_id",
            "created_at",
            postgresql_where=text("status = 'Pending'"),
        ),
        Index("ix_approval_tasks_process_id", "process_id"),
        Index("ix_approval_tasks_document_id", "document_id"),
    )

    process_id: Mapped[UUID] = mapped_column(ForeignKey("approval_processes.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalDecision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "approval_decisions"

    task_id: Mapped[UUID] = mapped_column(ForeignKey("approval_tasks.id", ondelete="CASCADE"), nullable=False)
    process_id: Mapped[UUID] = mapped_column(ForeignKey("approval_processes.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    approver_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
