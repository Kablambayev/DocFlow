from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import status

from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.accounting.repository import AccountingRepository
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.document_types.models import DocumentType
from app.modules.document_types.models import VersionStatus
from app.modules.documents.models import DocumentApprovalStatus
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import DocumentCreate, DocumentUpdate
from app.modules.notifications.models import NotificationType
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import NotificationService
from app.modules.workflow.engine import WorkflowEngine


class DocumentService:
    def __init__(self, repository: DocumentRepository):
        self.repository = repository
        self.accounting_repository = AccountingRepository(self.repository.db)
        self.audit_service = AuditService(AuditRepository(self.repository.db))
        self.notification_service = NotificationService(NotificationRepository(self.repository.db))

    def list_documents(self, user_id: UUID):
        permissions = self._permissions(user_id)
        if self._is_admin(user_id, permissions):
            return self.repository.list()
        visible_documents: list = []
        document_type_cache: dict[UUID, DocumentType | None] = {}
        for document in self.repository.list():
            if self._can_access_document(document, user_id, permissions=permissions, document_type_cache=document_type_cache):
                visible_documents.append(document)
        return visible_documents

    def get_document(self, document_id: UUID, user_id: UUID | None = None):
        doc = self.repository.get(document_id)
        if doc is None:
            raise AppError("Document not found", code="DOCUMENT_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)
        if user_id is not None and not self._can_access_document(doc, user_id):
            raise AppError("Document access denied", code="DOCUMENT_ACCESS_DENIED", status_code=403)
        return doc

    def _get_document_unchecked(self, document_id: UUID):
        doc = self.repository.get(document_id)
        if doc is None:
            raise AppError("Document not found", code="DOCUMENT_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)
        return doc

    def _permissions(self, user_id: UUID) -> set[str]:
        return get_user_permission_codes(self.repository.db, user_id)

    def _is_admin(self, user_id: UUID, permissions: set[str] | None = None) -> bool:
        resolved_permissions = permissions if permissions is not None else self._permissions(user_id)
        return "admin.access" in resolved_permissions

    def _can_access_document(
        self,
        doc,
        user_id: UUID,
        *,
        permissions: set[str] | None = None,
        document_type_cache: dict[UUID, DocumentType | None] | None = None,
    ) -> bool:
        resolved_permissions = permissions if permissions is not None else self._permissions(user_id)
        return (
            self._is_admin(user_id, resolved_permissions)
            or doc.author_id == user_id
            or self.repository.user_has_task_for_document(doc.id, user_id)
            or self._has_payment_request_export_visibility(doc, resolved_permissions, document_type_cache=document_type_cache)
        )

    def _has_payment_request_export_visibility(
        self,
        doc,
        permissions: set[str],
        *,
        document_type_cache: dict[UUID, DocumentType | None] | None = None,
    ) -> bool:
        if "integration_1c.payment_request.send" not in permissions:
            return False
        if doc.approval_status != DocumentApprovalStatus.APPROVED:
            return False
        document_type = self._get_document_type_cached(doc.document_type_id, document_type_cache)
        return document_type is not None and document_type.code == "PaymentRequest"

    def _get_document_type_cached(
        self,
        document_type_id: UUID,
        document_type_cache: dict[UUID, DocumentType | None] | None,
    ) -> DocumentType | None:
        if document_type_cache is None:
            return self.repository.get_document_type(document_type_id)
        if document_type_id not in document_type_cache:
            document_type_cache[document_type_id] = self.repository.get_document_type(document_type_id)
        return document_type_cache[document_type_id]

    def _ensure_author(self, doc, user_id: UUID) -> None:
        if not self._is_admin(user_id) and doc.author_id != user_id:
            raise AppError("Document access denied", code="DOCUMENT_ACCESS_DENIED", status_code=403)

    def list_all_documents(self):
        return self.repository.list()

    def create_document(self, payload: DocumentCreate):
        self._validate_document_type_links(payload.document_type_id, payload.document_type_version_id)
        version = self.repository.get_document_type_version(payload.document_type_version_id)
        assert version is not None
        self._validate_data(payload.data_json or {}, version.schema_json)

        doc = self.repository.create(payload)
        self.audit_service.log("document", doc.id, "document_created", user_id=payload.author_id, new_values_json={"id": str(doc.id)})
        return doc

    def update_document(self, document_id: UUID, payload: DocumentUpdate, user_id: UUID):
        doc = self._get_document_unchecked(document_id)
        self._ensure_author(doc, user_id)
        if doc.approval_status not in [DocumentApprovalStatus.DRAFT, DocumentApprovalStatus.WITHDRAWN]:
            raise AppError(
                "Document cannot be edited in current status",
                code="DOCUMENT_EDIT_FORBIDDEN",
                status_code=status.HTTP_409_CONFLICT,
                details={"approval_status": doc.approval_status},
            )

        version = self.repository.get_document_type_version(doc.document_type_version_id)
        assert version is not None
        data_json = payload.data_json if payload.data_json is not None else doc.data_json
        self._validate_data(data_json or {}, version.schema_json)

        old_values = {"title": doc.title, "approval_status": doc.approval_status}
        updated = self.repository.update(doc, payload)
        self.audit_service.log(
            "document",
            updated.id,
            "document_updated",
            user_id=updated.author_id,
            old_values_json=old_values,
            new_values_json={"title": updated.title, "approval_status": updated.approval_status},
        )
        return updated

    def submit_document(self, document_id: UUID, user_id: UUID):
        doc = self._get_document_unchecked(document_id)
        self._ensure_author(doc, user_id)
        engine = WorkflowEngine(self.repository.db, self.audit_service)
        engine.submit_document(document_id, user_id)
        return self.get_document(document_id, user_id)

    def withdraw_document(self, document_id: UUID, user_id: UUID):
        doc = self._get_document_unchecked(document_id)
        self._ensure_author(doc, user_id)
        if doc.approval_status != DocumentApprovalStatus.ON_APPROVAL:
            raise AppError(
                "Document cannot be withdrawn in current status",
                code="DOCUMENT_WITHDRAW_FORBIDDEN",
                status_code=status.HTTP_409_CONFLICT,
                details={"approval_status": doc.approval_status},
            )

        process = self.repository.get_active_process(document_id)
        if process is None:
            raise AppError("Active approval process not found", code="ACTIVE_PROCESS_NOT_FOUND", status_code=404)

        cancelled_tasks = self.repository.cancel_process_and_tasks(process)
        doc.approval_status = DocumentApprovalStatus.WITHDRAWN
        for task in cancelled_tasks:
            self.notification_service.safe_create_notification(
                recipient_id=task.approver_id,
                actor_id=user_id,
                notification_type=NotificationType.DOCUMENT_WITHDRAWN,
                title="Документ отозван",
                message=f"Документ {doc.number} отозван автором",
                entity_type="document",
                entity_id=doc.id,
                document_id=doc.id,
                task_id=task.id,
                payload={"document_number": doc.number, "document_title": doc.title, "process_id": str(process.id)},
            )
        self.repository.db.commit()
        self.repository.db.refresh(doc)

        self.audit_service.log("document", doc.id, "document_withdrawn", user_id=user_id)
        return doc

    def _validate_document_type_links(self, document_type_id: UUID, document_type_version_id: UUID) -> None:
        doc_type = self.repository.get_document_type(document_type_id)
        if doc_type is None:
            raise AppError("Document type not found", code="DOCUMENT_TYPE_NOT_FOUND", status_code=404)

        version = self.repository.get_document_type_version(document_type_version_id)
        if version is None or version.document_type_id != document_type_id:
            raise AppError(
                "Document type version not found",
                code="DOCUMENT_TYPE_VERSION_NOT_FOUND",
                status_code=404,
            )
        if version.status != VersionStatus.PUBLISHED:
            raise AppError(
                "Document type version must be published",
                code="DOCUMENT_TYPE_VERSION_NOT_PUBLISHED",
                status_code=409,
            )

    def _validate_data(self, data_json: dict, schema_json: dict) -> None:
        errors: list[dict[str, str]] = []
        dictionary_getters = {
            "organizations": self.accounting_repository.get_active_organization,
            "counterparties": self.accounting_repository.get_active_counterparty,
            "counterparty_contracts": self.accounting_repository.get_active_contract,
            "currencies": self.accounting_repository.get_active_currency,
            "expense_items": self.accounting_repository.get_active_expense_item,
            "cash_flow_operation_types": self.accounting_repository.get_active_cash_flow_operation_type,
            "projects": self.accounting_repository.get_active_project,
        }
        sections = schema_json.get("sections", [])
        for section in sections:
            for field in section.get("fields", []):
                code = field.get("code")
                field_type = field.get("type")
                required = bool(field.get("required", False))
                value = data_json.get(code)

                if required and value in [None, "", [], {}]:
                    errors.append({"field": code, "message": "Field is required"})
                    continue

                if value is None:
                    continue

                if field_type in ["string", "text"] and not isinstance(value, str):
                    errors.append({"field": code, "message": "Value must be a string"})
                elif field_type == "integer" and not isinstance(value, int):
                    errors.append({"field": code, "message": "Value must be an integer"})
                elif field_type in ["decimal", "money"] and not isinstance(value, (int, float)):
                    errors.append({"field": code, "message": "Value must be a number"})
                elif field_type == "boolean" and not isinstance(value, bool):
                    errors.append({"field": code, "message": "Value must be a boolean"})
                elif field_type in ["date", "datetime"]:
                    if not isinstance(value, str):
                        errors.append({"field": code, "message": "Value must be an ISO datetime string"})
                    else:
                        try:
                            datetime.fromisoformat(value.replace("Z", "+00:00"))
                        except ValueError:
                            errors.append({"field": code, "message": "Invalid ISO datetime format"})
                elif field_type == "enum":
                    options = ((field.get("settings") or {}).get("options") if isinstance(field.get("settings"), dict) else None) or []
                    allowed_values: list = []
                    for option in options:
                        if isinstance(option, dict):
                            allowed_values.append(option.get("value"))
                        else:
                            allowed_values.append(option)
                    if allowed_values and value not in allowed_values:
                        errors.append({"field": code, "message": "Value is not allowed"})
                elif field_type == "dictionary":
                    if not isinstance(value, str):
                        errors.append({"field": code, "message": "Dictionary value must be a UUID string"})
                        continue
                    try:
                        item_id = UUID(value)
                    except ValueError:
                        errors.append({"field": code, "message": "Dictionary value must be a UUID string"})
                        continue

                    settings = field.get("settings") if isinstance(field.get("settings"), dict) else {}
                    dictionary_name = settings.get("dictionary") if isinstance(settings, dict) else None
                    getter = dictionary_getters.get(str(dictionary_name)) if dictionary_name else None
                    if getter is None:
                        errors.append({"field": code, "message": f"Unknown dictionary: {dictionary_name}"})
                        continue

                    dictionary_item = getter(item_id)
                    if dictionary_item is None:
                        errors.append({"field": code, "message": "Dictionary item does not exist or inactive"})
                        continue

                    if str(dictionary_name) == "counterparty_contracts":
                        selected_organization_id = data_json.get("organization_id")
                        selected_counterparty_id = data_json.get("counterparty_id")
                        try:
                            org_id = UUID(selected_organization_id) if isinstance(selected_organization_id, str) else None
                            cp_id = UUID(selected_counterparty_id) if isinstance(selected_counterparty_id, str) else None
                        except ValueError:
                            org_id = None
                            cp_id = None

                        if org_id is None or cp_id is None:
                            errors.append(
                                {
                                    "field": code,
                                    "message": "Contract requires selected organization_id and counterparty_id",
                                }
                            )
                            continue

                        if dictionary_item.organization_id != org_id or dictionary_item.counterparty_id != cp_id:
                            errors.append(
                                {
                                    "field": code,
                                    "message": "Contract does not match selected organization and counterparty",
                                }
                            )

        if errors:
            raise AppError(
                "Document data validation failed",
                code="DOCUMENT_VALIDATION_ERROR",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                details={
                    "field": errors[0]["field"],
                    "reason": errors[0]["message"],
                    "errors": errors,
                },
            )

