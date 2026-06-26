from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.files.repository import FileRepository
from app.modules.files.schemas import DeleteFileResponse, DocumentFileRead
from app.modules.files.service import FileService
from app.modules.files.storage import LocalStorageProvider, get_storage_provider
from app.modules.users.models import User

router = APIRouter(tags=["files"])


def get_service(db: Session = Depends(get_db)) -> FileService:
    return FileService(FileRepository(db), get_storage_provider())


@router.get("/documents/{document_id}/files", response_model=list[DocumentFileRead])
def list_document_files(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FileService = Depends(get_service),
) -> list[DocumentFileRead]:
    return service.list_document_files(document_id, current_user)


@router.post("/documents/{document_id}/files", response_model=DocumentFileRead)
async def upload_document_file(
    document_id: UUID,
    file: UploadFile = File(...),
    field_code: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    service: FileService = Depends(get_service),
) -> DocumentFileRead:
    content = await file.read()
    return service.upload_document_file(
        document_id=document_id,
        user=current_user,
        file_name=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        field_code=field_code,
    )


@router.get("/files/{file_id}/download")
def download_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FileService = Depends(get_service),
) -> FileResponse:
    item = service.get_download(file_id, current_user)
    storage = service.storage
    if not isinstance(storage, LocalStorageProvider):
        raise RuntimeError("Current router supports local storage downloads only")
    path: Path = storage.path_for(item.storage_key)
    return FileResponse(
        path=path,
        media_type=item.content_type,
        filename=item.file_name,
    )


@router.delete("/files/{file_id}", response_model=DeleteFileResponse)
def delete_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FileService = Depends(get_service),
) -> DeleteFileResponse:
    service.delete_file(file_id, current_user)
    return DeleteFileResponse()
