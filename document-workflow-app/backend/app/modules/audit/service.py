from __future__ import annotations

from uuid import UUID

from app.modules.audit.repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

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
    ):
        return self.repository.log(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            old_values_json=old_values_json,
            new_values_json=new_values_json,
            ip_address=ip_address,
            user_agent=user_agent,
        )

