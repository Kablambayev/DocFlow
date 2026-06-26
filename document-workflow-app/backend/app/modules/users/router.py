from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


@router.get("", response_model=list[UserRead])
def list_users(service: UserService = Depends(get_service)) -> list[UserRead]:
    return service.list_users()


@router.post("", response_model=UserRead)
def create_user(payload: UserCreate, service: UserService = Depends(get_service)) -> UserRead:
    return service.create_user(payload)


@router.get("/{id}", response_model=UserRead)
def get_user(id: UUID, service: UserService = Depends(get_service)) -> UserRead:
    return service.get_user(id)


@router.put("/{id}", response_model=UserRead)
def update_user(id: UUID, payload: UserUpdate, service: UserService = Depends(get_service)) -> UserRead:
    return service.update_user(id, payload)
