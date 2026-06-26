from __future__ import annotations

import re
from pathlib import PurePath
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.documents.models import DocumentApprovalStatus
from app.modules.files.repository import FileRepository
from app.modules.files.storage import StorageProvider
from app.modules.users.models import User


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class FileService:
    def __init__(self, repository: FileRepository, storage: StorageProvider):
        self.repository = repository
        self.storage = storage
        self.audit_service = AuditService(AuditRepository(self.repository.db))

    def list_document_files(self, document_id: UUID, user: User):
        document = self._get_document(document_id)
        self._require_permission(user.id, "document_file.read")
        self._ensure_can_access_document(document, user.id)
        return self.repository.list_for_document(document_id)

    def upload_document_file(
        self,
        *,
        document_id: UUID,
        user: User,
        file_name: str,
        content_type: str,
        content: bytes,
        field_code: str | None,
    ):
        document = self._get_document(document_id)
        self._require_permission(user.id, "document_file.upload")
        self._ensure_can_access_document(document, user.id)
        self._ensure_can_mutate_document_files(document, user.id)
        self._validate_content(content)

        safe_name = self._safe_filename(file_name)
        self._validate_extension(safe_name)
        file_id = uuid4()
        storage_key = f"documents/{document_id}/{file_id}_{safe_name}"
        self.storage.save(content, storage_key)
        item = self.repository.create_file(
            file_id=file_id,
            document_id=document_id,
            field_code=field_code,
            file_name=safe_name,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(content),
            storage_key=storage_key,
            uploaded_by=user.id,
        )
        self.audit_service.log(
            "document_file",
            item.id,
            "document_file_uploaded",
            user_id=user.id,
            new_values_json={
                "document_id": str(document_id),
                "file_id": str(item.id),
                "file_name": item.file_name,
                "field_code": item.field_code,
            },
        )
        return item

    def get_download(self, file_id: UUID, user: User):
        item = self._get_file(file_id)
        document = self._get_document(item.document_id)
        self._require_permission(user.id, "document_file.read")
        self._ensure_can_access_document(document, user.id)
        if not self.storage.exists(item.storage_key):
            raise AppError("File content not found", code="FILE_CONTENT_NOT_FOUND", status_code=404)
        self.audit_service.log(
            "document_file",
            item.id,
            "document_file_downloaded",
            user_id=user.id,
            new_values_json={
                "document_id": str(item.document_id),
                "file_id": str(item.id),
                "file_name": item.file_name,
                "field_code": item.field_code,
            },
        )
        return item

    def delete_file(self, file_id: UUID, user: User) -> None:
        item = self._get_file(file_id)
        document = self._get_document(item.document_id)
        self._require_permission(user.id, "document_file.delete")
        self._ensure_can_mutate_document_files(document, user.id)
        self.repository.soft_delete(item, user.id)
        self.audit_service.log(
            "document_file",
            item.id,
            "document_file_deleted",
            user_id=user.id,
            old_values_json={
                "document_id": str(item.document_id),
                "file_id": str(item.id),
                "file_name": item.file_name,
                "field_code": item.field_code,
            },
        )

    def _get_document(self, document_id: UUID):
        document = self.repository.get_document(document_id)
        if document is None:
            raise AppError("Document not found", code="DOCUMENT_NOT_FOUND", status_code=404)
        return document

    def _get_file(self, file_id: UUID):
        item = self.repository.get_file(file_id)
        if item is None or item.is_deleted:
            raise AppError("File not found", code="FILE_NOT_FOUND", status_code=404)
        return item

    def _permissions(self, user_id: UUID) -> set[str]:
        return get_user_permission_codes(self.repository.db, user_id)

    def _is_admin(self, user_id: UUID) -> bool:
        return "admin.access" in self._permissions(user_id)

    def _require_permission(self, user_id: UUID, permission_code: str) -> None:
        permissions = self._permissions(user_id)
        if "admin.access" not in permissions and permission_code not in permissions:
            raise AppError(
                "Permission required",
                code="PERMISSION_DENIED",
                status_code=403,
                details={"permission": permission_code},
            )

    def _ensure_can_access_document(self, document, user_id: UUID) -> None:
        if self._is_admin(user_id) or document.author_id == user_id:
            return
        if self.repository.user_has_document_task(document.id, user_id):
            return
        raise AppError("Document access denied", code="DOCUMENT_ACCESS_DENIED", status_code=403)

    def _ensure_can_mutate_document_files(self, document, user_id: UUID) -> None:
        if document.approval_status not in [DocumentApprovalStatus.DRAFT, DocumentApprovalStatus.WITHDRAWN]:
            raise AppError(
                "Files can be changed only in Draft or Withdrawn documents",
                code="DOCUMENT_FILE_MUTATION_FORBIDDEN",
                status_code=409,
                details={"approval_status": document.approval_status},
            )
        if not self._is_admin(user_id) and document.author_id != user_id:
            raise AppError("Document access denied", code="DOCUMENT_ACCESS_DENIED", status_code=403)

    def _validate_content(self, content: bytes) -> None:
        if not content:
            raise AppError("File is empty", code="FILE_EMPTY", status_code=422)
        max_size = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise AppError(
                "File is too large",
                code="FILE_TOO_LARGE",
                status_code=413,
                details={"max_size_mb": settings.max_upload_size_mb},
            )

    def _safe_filename(self, file_name: str) -> str:
        name = PurePath(file_name or "file").name
        name = SAFE_FILENAME_RE.sub("_", name).strip("._")
        return name or "file"

    def _validate_extension(self, safe_name: str) -> None:
        suffix = PurePath(safe_name).suffix.lower()
        if suffix not in settings.allowed_file_extension_set:
            raise AppError("File extension is not allowed", code="FILE_EXTENSION_NOT_ALLOWED", status_code=422)
