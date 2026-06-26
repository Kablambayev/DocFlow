from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AppError
from app.modules.workflow.repository import WorkflowRepository


class ApproverResolver:
    def __init__(self, repository: WorkflowRepository):
        self.repository = repository

    def resolve(self, resolver_config: dict) -> list[UUID]:
        resolver_type = resolver_config.get("type")
        if resolver_type == "specific_user":
            user_id = resolver_config.get("userId")
            if not user_id:
                return []
            return [UUID(user_id)]
        if resolver_type == "role":
            role_code = resolver_config.get("roleCode")
            if not role_code:
                return []
            return self.repository.find_active_users_by_role_code(role_code)

        raise AppError(f"Unsupported resolver type: {resolver_type}", code="resolver_not_supported", status_code=400)
