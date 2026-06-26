from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        entity_type: str,
        entity_id: UUID,
        action: str,
        user_id: UUID | None = None,
        old_values_json: dict | None = None,
        new_values_json: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            old_values_json=old_values_json,
            new_values_json=new_values_json,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

