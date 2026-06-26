from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.roles.models import Role
from app.modules.roles.schemas import RoleCreate, RoleUpdate
from app.modules.users.models import Permission, User


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_roles(self) -> list[Role]:
        return list(
            self.db.scalars(
                select(Role).options(selectinload(Role.permissions)).order_by(Role.created_at.desc())
            )
        )

    def get_role(self, role_id: UUID) -> Role | None:
        return self.db.scalar(
            select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
        )

    def get_role_by_code(self, code: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.code == code))

    def create_role(self, payload: RoleCreate) -> Role:
        role = Role(**payload.model_dump())
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return self.get_role(role.id) or role

    def update_role(self, role: Role, payload: RoleUpdate) -> Role:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(role, key, value)
        self.db.commit()
        self.db.refresh(role)
        return self.get_role(role.id) or role

    def list_permissions(self) -> list[Permission]:
        return list(self.db.scalars(select(Permission).order_by(Permission.code.asc())))

    def get_permission(self, permission_id: UUID) -> Permission | None:
        return self.db.get(Permission, permission_id)

    def get_user(self, user_id: UUID) -> User | None:
        return self.db.scalar(
            select(User).where(User.id == user_id).options(selectinload(User.roles).selectinload(Role.permissions))
        )

    def add_permission_to_role(self, role: Role, permission: Permission) -> Role:
        if permission not in role.permissions:
            role.permissions.append(permission)
            self.db.commit()
        return self.get_role(role.id) or role

    def remove_permission_from_role(self, role: Role, permission: Permission) -> Role:
        if permission in role.permissions:
            role.permissions.remove(permission)
            self.db.commit()
        return self.get_role(role.id) or role

    def add_role_to_user(self, user: User, role: Role) -> User:
        if role not in user.roles:
            user.roles.append(role)
            self.db.commit()
        self.db.refresh(user)
        return user

    def remove_role_from_user(self, user: User, role: Role) -> User:
        if role in user.roles:
            user.roles.remove(role)
            self.db.commit()
        self.db.refresh(user)
        return user
