from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.modules.workflow.models import ApprovalDecision, ApprovalProcess


def resolve_document_approved_at(db: Session, document_id: UUID, fallback: datetime) -> datetime:
    finished_at = db.scalar(
        select(ApprovalProcess.finished_at)
        .where(ApprovalProcess.document_id == document_id, ApprovalProcess.finished_at.is_not(None))
        .order_by(desc(ApprovalProcess.finished_at))
    )
    if finished_at is not None:
        return finished_at

    latest_approved_decision_at = db.scalar(
        select(ApprovalDecision.created_at)
        .where(ApprovalDecision.document_id == document_id, ApprovalDecision.decision == "Approve")
        .order_by(desc(ApprovalDecision.created_at))
    )
    if latest_approved_decision_at is not None:
        return latest_approved_decision_at

    return fallback