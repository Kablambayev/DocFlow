from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.roles.repository import RoleRepository
from app.modules.roles.schemas import RoleCreate, RoleUpdate


class RoleService:
    def __init__(self, repository: RoleRepository):
        self.repository = repository
        self.audit_service = AuditService(AuditRepository(self.repository.db))

    def list_roles(self):
        return self.repository.list_roles()

    def get_role(self, role_id: UUID):
        role = self.repository.get_role(role_id)
        if role is None:
            raise AppError("Role not found", code="ROLE_NOT_FOUND", status_code=404)
        return role

    def create_role(self, payload: RoleCreate, user_id: UUID):
        if self.repository.get_role_by_code(payload.code) is not None:
            raise AppError("Role code already exists", code="ROLE_CODE_EXISTS", status_code=409)
        role = self.repository.create_role(payload)
        self.audit_service.log("role", role.id, "role_created", user_id=user_id, new_values_json=payload.model_dump())
        return role

    def update_role(self, role_id: UUID, payload: RoleUpdate, user_id: UUID):
        role = self.get_role(role_id)
        old_values = {"name": role.name, "description": role.description, "is_active": role.is_active}
        updated = self.repository.update_role(role, payload)
        self.audit_service.log(
            "role",
            updated.id,
            "role_updated",
            user_id=user_id,
            old_values_json=old_values,
            new_values_json=payload.model_dump(exclude_unset=True),
        )
        return updated

    def list_permissions(self):
        return self.repository.list_permissions()

    def add_permission_to_role(self, role_id: UUID, permission_id: UUID, user_id: UUID):
        role = self.get_role(role_id)
        permission = self.repository.get_permission(permission_id)
        if permission is None:
            raise AppError("Permission not found", code="PERMISSION_NOT_FOUND", status_code=404)
        updated = self.repository.add_permission_to_role(role, permission)
        self.audit_service.log(
            "role",
            role.id,
            "role_permission_added",
            user_id=user_id,
            new_values_json={"permission": permission.code},
        )
        return updated

    def remove_permission_from_role(self, role_id: UUID, permission_id: UUID, user_id: UUID):
        role = self.get_role(role_id)
        permission = self.repository.get_permission(permission_id)
        if permission is None:
            raise AppError("Permission not found", code="PERMISSION_NOT_FOUND", status_code=404)
        updated = self.repository.remove_permission_from_role(role, permission)
        self.audit_service.log(
            "role",
            role.id,
            "role_permission_removed",
            user_id=user_id,
            old_values_json={"permission": permission.code},
        )
        return updated

    def list_user_roles(self, user_id: UUID):
        user = self.repository.get_user(user_id)
        if user is None:
            raise AppError("User not found", code="USER_NOT_FOUND", status_code=404)
        return user.roles

    def list_user_permissions(self, user_id: UUID):
        user = self.repository.get_user(user_id)
        if user is None:
            raise AppError("User not found", code="USER_NOT_FOUND", status_code=404)
        codes = get_user_permission_codes(self.repository.db, user_id)
        return [permission for permission in self.repository.list_permissions() if permission.code in codes]

    def add_role_to_user(self, user_id: UUID, role_id: UUID, actor_id: UUID):
        user = self.repository.get_user(user_id)
        if user is None:
            raise AppError("User not found", code="USER_NOT_FOUND", status_code=404)
        role = self.get_role(role_id)
        updated = self.repository.add_role_to_user(user, role)
        self.audit_service.log(
            "user",
            user.id,
            "user_role_added",
            user_id=actor_id,
            new_values_json={"role": role.code},
        )
        return updated.roles

    def remove_role_from_user(self, user_id: UUID, role_id: UUID, actor_id: UUID):
        user = self.repository.get_user(user_id)
        if user is None:
            raise AppError("User not found", code="USER_NOT_FOUND", status_code=404)
        role = self.get_role(role_id)
        updated = self.repository.remove_role_from_user(user, role)
        self.audit_service.log(
            "user",
            user.id,
            "user_role_removed",
            user_id=actor_id,
            old_values_json={"role": role.code},
        )
        return updated.roles
