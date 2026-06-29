from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.documents.models import Document
from app.modules.integration.log_models import IntegrationOperationLog
from app.modules.users.models import User


class IntegrationLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **values) -> IntegrationOperationLog:
        item = IntegrationOperationLog(**values)
        self.db.add(item)
        self.db.flush()
        return item

    def save(self, item: IntegrationOperationLog) -> IntegrationOperationLog:
        self.db.add(item)
        self.db.flush()
        return item

    def get_by_id(self, log_id: UUID) -> IntegrationOperationLog | None:
        return self.db.get(IntegrationOperationLog, log_id)

    def get_with_relations(self, log_id: UUID):
        stmt = (
            select(IntegrationOperationLog, Document.number, User.full_name)
            .outerjoin(Document, Document.id == IntegrationOperationLog.document_id)
            .outerjoin(User, User.id == IntegrationOperationLog.initiated_by)
            .where(IntegrationOperationLog.id == log_id)
        )
        return self.db.execute(stmt).first()

    def list_logs(
        self,
        *,
        direction: str | None,
        operation_type: str | None,
        status: str | None,
        document_id: UUID | None,
        date_from: datetime | date | None,
        date_to: datetime | date | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ):
        stmt = select(IntegrationOperationLog, Document.number, User.full_name).outerjoin(
            Document, Document.id == IntegrationOperationLog.document_id
        ).outerjoin(User, User.id == IntegrationOperationLog.initiated_by)
        filtered_stmt = self._apply_filters(
            stmt=stmt,
            direction=direction,
            operation_type=operation_type,
            status=status,
            document_id=document_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        total_stmt = self._apply_filters(
            stmt=select(func.count(IntegrationOperationLog.id)),
            direction=direction,
            operation_type=operation_type,
            status=status,
            document_id=document_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        total = self.db.scalar(total_stmt) or 0
        sort_column = getattr(IntegrationOperationLog, sort_by, IntegrationOperationLog.created_at)
        if sort_order == "asc":
            filtered_stmt = filtered_stmt.order_by(sort_column.asc())
        else:
            filtered_stmt = filtered_stmt.order_by(sort_column.desc())
        items = self.db.execute(filtered_stmt.limit(limit).offset(offset)).all()
        return items, total

    def _apply_filters(
        self,
        *,
        stmt: Select,
        direction: str | None,
        operation_type: str | None,
        status: str | None,
        document_id: UUID | None,
        date_from: datetime | date | None,
        date_to: datetime | date | None,
        search: str | None,
    ) -> Select:
        if direction:
            stmt = stmt.where(IntegrationOperationLog.direction == direction)
        if operation_type:
            stmt = stmt.where(IntegrationOperationLog.operation_type == operation_type)
        if status:
            stmt = stmt.where(IntegrationOperationLog.status == status)
        if document_id:
            stmt = stmt.where(IntegrationOperationLog.document_id == document_id)
        if date_from:
            stmt = stmt.where(IntegrationOperationLog.created_at >= self._normalize_date_start(date_from))
        if date_to:
            stmt = stmt.where(IntegrationOperationLog.created_at <= self._normalize_date_end(date_to))
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    IntegrationOperationLog.correlation_id.ilike(pattern),
                    IntegrationOperationLog.idempotency_key.ilike(pattern),
                    IntegrationOperationLog.error_code.ilike(pattern),
                    IntegrationOperationLog.error_message.ilike(pattern),
                    IntegrationOperationLog.request_url.ilike(pattern),
                )
            )
        return stmt

    def _normalize_date_start(self, value: datetime | date) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    def _normalize_date_end(self, value: datetime | date) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return datetime.combine(value, time.max, tzinfo=timezone.utc)
