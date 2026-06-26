from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_user_permission_codes, require_permission
from app.db.session import get_db
from app.modules.roles.repository import RoleRepository
from app.modules.roles.schemas import (
    PermissionRead,
    RoleCreate,
    RolePermissionRequest,
    RoleRead,
    RoleUpdate,
    UserRoleRequest,
)
from app.modules.roles.service import RoleService
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(tags=["roles"])


def get_service(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(RoleRepository(db))


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user


@router.get("/me/permissions", response_model=list[str])
def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[str]:
    return sorted(get_user_permission_codes(db, current_user.id))


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    _: User = Depends(require_permission("role.read")),
    service: RoleService = Depends(get_service),
) -> list[RoleRead]:
    return service.list_roles()


@router.post("/roles", response_model=RoleRead)
def create_role(
    payload: RoleCreate,
    current_user: User = Depends(require_permission("role.create")),
    service: RoleService = Depends(get_service),
) -> RoleRead:
    return service.create_role(payload, current_user.id)


@router.get("/roles/{id}", response_model=RoleRead)
def get_role(
    id: UUID,
    _: User = Depends(require_permission("role.read")),
    service: RoleService = Depends(get_service),
) -> RoleRead:
    return service.get_role(id)


@router.put("/roles/{id}", response_model=RoleRead)
def update_role(
    id: UUID,
    payload: RoleUpdate,
    current_user: User = Depends(require_permission("role.update")),
    service: RoleService = Depends(get_service),
) -> RoleRead:
    return service.update_role(id, payload, current_user.id)


@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(
    _: User = Depends(require_permission("permission.read")),
    service: RoleService = Depends(get_service),
) -> list[PermissionRead]:
    return service.list_permissions()


@router.post("/roles/{id}/permissions", response_model=RoleRead)
def add_role_permission(
    id: UUID,
    payload: RolePermissionRequest,
    current_user: User = Depends(require_permission("role.update")),
    service: RoleService = Depends(get_service),
) -> RoleRead:
    return service.add_permission_to_role(id, payload.permission_id, current_user.id)


@router.delete("/roles/{id}/permissions/{permission_id}", response_model=RoleRead)
def remove_role_permission(
    id: UUID,
    permission_id: UUID,
    current_user: User = Depends(require_permission("role.update")),
    service: RoleService = Depends(get_service),
) -> RoleRead:
    return service.remove_permission_from_role(id, permission_id, current_user.id)


@router.get("/users/{id}/roles", response_model=list[RoleRead])
def list_user_roles(
    id: UUID,
    _: User = Depends(require_permission("role.read")),
    service: RoleService = Depends(get_service),
) -> list[RoleRead]:
    return service.list_user_roles(id)


@router.post("/users/{id}/roles", response_model=list[RoleRead])
def add_user_role(
    id: UUID,
    payload: UserRoleRequest,
    current_user: User = Depends(require_permission("role.update")),
    service: RoleService = Depends(get_service),
) -> list[RoleRead]:
    return service.add_role_to_user(id, payload.role_id, current_user.id)


@router.delete("/users/{id}/roles/{role_id}", response_model=list[RoleRead])
def remove_user_role(
    id: UUID,
    role_id: UUID,
    current_user: User = Depends(require_permission("role.update")),
    service: RoleService = Depends(get_service),
) -> list[RoleRead]:
    return service.remove_role_from_user(id, role_id, current_user.id)


@router.get("/users/{id}/permissions", response_model=list[PermissionRead])
def list_user_permissions(
    id: UUID,
    _: User = Depends(require_permission("permission.read")),
    service: RoleService = Depends(get_service),
) -> list[PermissionRead]:
    return service.list_user_permissions(id)
