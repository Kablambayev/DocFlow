from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.session import get_db
from app.modules.roles.models import Role, role_permissions_table
from app.modules.users.models import Permission, User, user_roles_table


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    if x_user_id is None:
        raise AppError("X-User-Id header is required", code="AUTH_REQUIRED", status_code=401)

    try:
        user_id = UUID(x_user_id)
    except ValueError as exc:
        raise AppError("X-User-Id header is invalid", code="AUTH_REQUIRED", status_code=401) from exc

    user = db.get(User, user_id)
    if user is None:
        raise AppError("User not found", code="USER_NOT_FOUND", status_code=401)
    if not user.is_active:
        raise AppError("User is inactive", code="USER_INACTIVE", status_code=403)
    return user


def get_user_permission_codes(db: Session, user_id: UUID) -> set[str]:
    stmt = (
        select(Permission.code)
        .join(role_permissions_table, role_permissions_table.c.permission_id == Permission.id)
        .join(Role, Role.id == role_permissions_table.c.role_id)
        .join(user_roles_table, user_roles_table.c.role_id == Role.id)
        .where(user_roles_table.c.user_id == user_id, Role.is_active.is_(True))
    )
    return set(db.scalars(stmt))


def user_has_permission(db: Session, user_id: UUID, permission_code: str) -> bool:
    permissions = get_user_permission_codes(db, user_id)
    return "admin.access" in permissions or permission_code in permissions


def require_permission(permission_code: str):
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not user_has_permission(db, current_user.id, permission_code):
            raise AppError(
                "Permission required",
                code="PERMISSION_DENIED",
                status_code=403,
                details={"permission": permission_code},
            )
        return current_user

    return dependency


def require_any_permission(*permission_codes: str):
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        permissions = get_user_permission_codes(db, current_user.id)
        if "admin.access" in permissions or any(code in permissions for code in permission_codes):
            return current_user
        raise AppError(
            "Permission required",
            code="PERMISSION_DENIED",
            status_code=403,
            details={"permissions": list(permission_codes)},
        )

    return dependency
