from __future__ import annotations

from uuid import UUID

from fastapi import status

from app.core.exceptions import AppError
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def list_users(self):
        return self.repository.list()

    def get_user(self, user_id: UUID):
        user = self.repository.get(user_id)
        if user is None:
            raise AppError("User not found", code="user_not_found", status_code=status.HTTP_404_NOT_FOUND)
        return user

    def create_user(self, payload: UserCreate):
        existing = self.repository.get_by_email(payload.email)
        if existing is not None:
            raise AppError("Email already exists", code="email_exists", status_code=status.HTTP_409_CONFLICT)
        return self.repository.create(payload)
