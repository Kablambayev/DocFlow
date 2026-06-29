from __future__ import annotations

from datetime import timezone, datetime
from uuid import UUID

from fastapi import status

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.accounting.repository import AccountingRepository
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.documents.models import DocumentApprovalStatus
from app.modules.integration.one_c.outbound_client import OneCOutboundClient
from app.modules.integration.one_c.payment_export_models import (
    PaymentRequest1CExport,
    PaymentRequest1CExportStatus,
)
from app.modules.integration.one_c.payment_export_repository import PaymentRequest1CExportRepository
from app.modules.integration.one_c.payment_export_schemas import PaymentRequest1CExportRead
from app.modules.integration.one_c.payment_export_service import PaymentRequest1CExportPresenter
from app.modules.notifications.models import NotificationType
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import NotificationService
from app.modules.workflow.models import ApprovalTask
from sqlalchemy import select


class OneCOutboundService:
    """Service for DocFlow -> 1C export orchestration."""

    def __init__(self, repository: PaymentRequest1CExportRepository, client: OneCOutboundClient):
        self.repository = repository
        self.client = client
        self.accounting_repository = AccountingRepository(self.repository.db)
        self.audit_service = AuditService(AuditRepository(self.repository.db))
        self.notification_service = NotificationService(NotificationRepository(self.repository.db))
        self.presenter = PaymentRequest1CExportPresenter()

    def get_export(self, document_id: UUID, current_user):
        document = self._get_document(document_id)
        self._require_read_access(document, current_user.id)
        export = self.repository.get_by_document_id(document_id)
        return self.presenter.get_export_response(export)

    def send_approved_payment_request_to_1c(self, document_id: UUID, current_user, force: bool = False):
        document = self._get_document(document_id)
        self._require_send_permission(current_user.id)
        self._validate_document_for_export(document)

        export = self.repository.get_by_document_id(document_id)
        if not force and export is not None and export.status in {
            PaymentRequest1CExportStatus.CREATED_IN_1C,
            PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C,
        }:
            return {
                "status": "already_exported",
                "export": PaymentRequest1CExportRead.model_validate(export).model_dump(mode="json"),
            }

        payload = self._build_payload(document)
        export = self._upsert_export(export, document_id=document.id, current_user_id=current_user.id, payload=payload)
        self._log_audit(
            action="integration_1c_payment_request_send_started",
            document=document,
            user_id=current_user.id,
            export_status=PaymentRequest1CExportStatus.PENDING,
            one_c_enabled=settings.one_c_enabled,
        )

        if settings.one_c_enabled:
            client_result = self.client.send_payment_request(payload)
        else:
            client_result = self.presenter.build_fake_response(document_id=document.id, payload=payload)

        export.response_payload = client_result
        export.status = PaymentRequest1CExportStatus.SENT
        self.repository.save(export)

        result_status = client_result.get("status")
        payment_order = self.presenter.normalize_payment_order(client_result.get("payment_order"))
        error = client_result.get("error") or {}
        if result_status == "created":
            export.status = PaymentRequest1CExportStatus.CREATED_IN_1C
            self._apply_payment_order(export, payment_order)
            self._log_audit(
                action="integration_1c_payment_request_created",
                document=document,
                user_id=current_user.id,
                export_status=export.status,
                payment_order=payment_order,
                one_c_enabled=settings.one_c_enabled,
            )
            self._notify_success(document, current_user.id, payment_order)
        elif result_status == "already_exists":
            export.status = PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C
            self._apply_payment_order(export, payment_order)
            self._log_audit(
                action="integration_1c_payment_request_already_exists",
                document=document,
                user_id=current_user.id,
                export_status=export.status,
                payment_order=payment_order,
                one_c_enabled=settings.one_c_enabled,
            )
            self._notify_success(document, current_user.id, payment_order)
        else:
            export.status = PaymentRequest1CExportStatus.FAILED
            export.error_code = error.get("code") or "ONE_C_EXPORT_FAILED"
            export.error_message = error.get("message") or "1C export failed"
            export.one_c_payment_order_external_id = None
            export.one_c_payment_order_number = None
            export.one_c_payment_order_date = None
            export.one_c_payment_order_amount = None
            export.one_c_payment_order_currency_code = None
            self._log_audit(
                action="integration_1c_payment_request_failed",
                document=document,
                user_id=current_user.id,
                export_status=export.status,
                payment_order=payment_order,
                one_c_enabled=settings.one_c_enabled,
            )
            self._notify_failure(document, current_user.id, export)

        self.repository.save(export)
        self.repository.db.commit()
        self.repository.db.refresh(export)
        return self.presenter.build_send_response(export=export, one_c_enabled=settings.one_c_enabled)

    def _get_document(self, document_id: UUID):
        document = self.repository.get_document(document_id)
        if document is None:
            raise AppError("Document not found", code="DOCUMENT_NOT_FOUND", status_code=404)
        return document

    def _validate_document_for_export(self, document) -> None:
        document_type = self.repository.get_document_type(document.document_type_id)
        if document_type is None or document_type.code != "PaymentRequest":
            raise AppError(
                "Only PaymentRequest can be sent to 1C",
                code="UNSUPPORTED_DOCUMENT_TYPE",
                status_code=status.HTTP_409_CONFLICT,
            )
        if document.approval_status != DocumentApprovalStatus.APPROVED:
            raise AppError(
                "Only approved PaymentRequest can be sent to 1C",
                code="DOCUMENT_NOT_APPROVED",
                status_code=status.HTTP_409_CONFLICT,
            )
        if document.approval_status == DocumentApprovalStatus.ARCHIVED:
            raise AppError(
                "Only approved PaymentRequest can be sent to 1C",
                code="DOCUMENT_NOT_APPROVED",
                status_code=status.HTTP_409_CONFLICT,
            )

    def _build_payload(self, document) -> dict:
        data = document.data_json or {}
        organization = self._require_external_dictionary_item(
            field="organization_id",
            value=data.get("organization_id"),
            getter=self.accounting_repository.get_active_organization,
            attr="external_id",
            reason="Organization external_id not found",
        )
        counterparty = self._require_external_dictionary_item(
            field="counterparty_id",
            value=data.get("counterparty_id"),
            getter=self.accounting_repository.get_active_counterparty,
            attr="external_id",
            reason="Counterparty external_id not found",
        )
        contract = self._require_external_dictionary_item(
            field="contract_id",
            value=data.get("contract_id"),
            getter=self.accounting_repository.get_active_contract,
            attr="external_id",
            reason="Contract external_id not found",
        )
        currency = self._require_external_dictionary_item(
            field="currency_id",
            value=data.get("currency_id"),
            getter=self.accounting_repository.get_active_currency,
            attr="external_id",
            reason="Currency external_id not found",
        )
        expense_item = self._require_external_dictionary_item(
            field="expense_item_id",
            value=data.get("expense_item_id"),
            getter=self.accounting_repository.get_active_expense_item,
            attr="external_id",
            reason="Expense item external_id not found",
        )
        cash_flow_operation_type = self._require_external_dictionary_item(
            field="cash_flow_operation_type_id",
            value=data.get("cash_flow_operation_type_id"),
            getter=self.accounting_repository.get_active_cash_flow_operation_type,
            attr="code",
            reason="Cash flow operation type code not found",
        )
        project = self._require_external_dictionary_item(
            field="project_id",
            value=data.get("project_id"),
            getter=self.accounting_repository.get_active_project,
            attr="code",
            reason="Project code not found",
        )
        amount = data.get("amount")
        if amount is None:
            self._raise_mapping_error(field="amount", reason="Amount not found")
        author = self.repository.get_user(document.author_id)
        if author is None:
            self._raise_mapping_error(field="author", reason="Document author not found")

        approved_at = (
            self.repository.get_approval_process_finished_at(document.id)
            or self.repository.get_last_approval_decision_at(document.id)
            or document.updated_at
        )

        return {
            "request_id": str(document.id),
            "request_number": document.number,
            "request_date": document.document_date.date().isoformat(),
            "organization_external_id": organization.external_id,
            "counterparty_external_id": counterparty.external_id,
            "contract_external_id": contract.external_id,
            "currency_external_id": currency.external_id,
            "expense_item_external_id": expense_item.external_id,
            "cash_flow_operation_type_code": cash_flow_operation_type.code,
            "project_code": project.code,
            "amount": amount,
            "payment_purpose": data.get("payment_purpose") or data.get("paymentPurpose"),
            "comment": data.get("comment"),
            "author": {
                "id": str(author.id),
                "email": author.email,
                "name": author.full_name,
            },
            "approved_at": approved_at.isoformat(),
        }

    def _require_external_dictionary_item(self, *, field: str, value, getter, attr: str, reason: str):
        if not isinstance(value, str):
            self._raise_mapping_error(field=field, reason=reason)
        try:
            item_id = UUID(value)
        except ValueError:
            self._raise_mapping_error(field=field, reason=reason)
        item = getter(item_id)
        if item is None or not getattr(item, attr, None):
            self._raise_mapping_error(field=field, reason=reason)
        return item

    def _raise_mapping_error(self, *, field: str, reason: str) -> None:
        raise AppError(
            "Cannot map PaymentRequest data to 1C payload",
            code="EXPORT_MAPPING_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details={"field": field, "reason": reason},
        )

    def _upsert_export(self, export: PaymentRequest1CExport | None, *, document_id: UUID, current_user_id: UUID, payload: dict) -> PaymentRequest1CExport:
        now = datetime.now(timezone.utc)
        if export is None:
            export = self.repository.create(
                document_id=document_id,
                status=PaymentRequest1CExportStatus.PENDING,
                sent_at=now,
                sent_by=current_user_id,
                request_payload=payload,
                response_payload={},
                error_code=None,
                error_message=None,
            )
            return export
        export.status = PaymentRequest1CExportStatus.PENDING
        export.sent_at = now
        export.sent_by = current_user_id
        export.request_payload = payload
        export.response_payload = {}
        export.error_code = None
        export.error_message = None
        export.one_c_payment_order_external_id = None
        export.one_c_payment_order_number = None
        export.one_c_payment_order_date = None
        export.one_c_payment_order_amount = None
        export.one_c_payment_order_currency_code = None
        self.repository.save(export)
        return export

    def _apply_payment_order(self, export: PaymentRequest1CExport, payment_order: dict) -> None:
        export.error_code = None
        export.error_message = None
        export.one_c_payment_order_external_id = payment_order.get("external_id")
        export.one_c_payment_order_number = payment_order.get("number")
        export.one_c_payment_order_date = payment_order.get("date")
        export.one_c_payment_order_amount = payment_order.get("amount")
        export.one_c_payment_order_currency_code = payment_order.get("currency_code")

    def _permissions(self, user_id: UUID) -> set[str]:
        return get_user_permission_codes(self.repository.db, user_id)

    def _is_admin(self, user_id: UUID) -> bool:
        return "admin.access" in self._permissions(user_id)

    def _ensure_can_access_document(self, document, user_id: UUID) -> None:
        if self._is_admin(user_id) or document.author_id == user_id:
            return
        if self.repository.db.scalar(
            select(ApprovalTask.id).where(ApprovalTask.document_id == document.id, ApprovalTask.approver_id == user_id)
        ) is not None:
            return
        raise AppError("Document access denied", code="DOCUMENT_ACCESS_DENIED", status_code=403)

    def _require_send_permission(self, user_id: UUID) -> None:
        if not self._is_admin(user_id) and "integration_1c.payment_request.send" not in self._permissions(user_id):
            raise AppError("Permission required", code="PERMISSION_DENIED", status_code=403, details={"permission": "integration_1c.payment_request.send"})

    def _require_read_access(self, document, user_id: UUID) -> None:
        permissions = self._permissions(user_id)
        if "admin.access" not in permissions and "document.read" not in permissions and "accounting.read" not in permissions:
            raise AppError("Permission required", code="PERMISSION_DENIED", status_code=403, details={"permissions": ["document.read", "accounting.read"]})
        self._ensure_can_access_document(document, user_id)

    def _log_audit(self, *, action: str, document, user_id: UUID, export_status: str, one_c_enabled: bool, payment_order: dict | None = None) -> None:
        payment_order = payment_order or {}
        self.audit_service.log(
            "document",
            document.id,
            action,
            user_id=user_id,
            new_values_json={
                "document_id": str(document.id),
                "request_number": document.number,
                "export_status": export_status,
                "one_c_payment_order_external_id": payment_order.get("external_id"),
                "one_c_payment_order_number": payment_order.get("number"),
                "one_c_enabled": one_c_enabled,
            },
        )

    def _notify_success(self, document, actor_id: UUID, payment_order: dict) -> None:
        number = payment_order.get("number") or payment_order.get("external_id") or "-"
        self.notification_service.safe_create_notification(
            recipient_id=document.author_id,
            actor_id=actor_id,
            notification_type=NotificationType.INTEGRATION_1C_PAYMENT_ORDER_CREATED,
            title="Платежное поручение создано в 1С",
            message=f"По заявке {document.number} создано платежное поручение {number}",
            entity_type="document",
            entity_id=document.id,
            document_id=document.id,
            payload={"payment_order_number": number, "document_number": document.number},
            dedupe=False,
        )

    def _notify_failure(self, document, actor_id: UUID, export: PaymentRequest1CExport) -> None:
        recipients = {document.author_id}
        if actor_id != document.author_id:
            recipients.add(actor_id)
        self.notification_service.safe_notify_users(
            recipients,
            actor_id=actor_id,
            notification_type=NotificationType.INTEGRATION_1C_PAYMENT_REQUEST_FAILED,
            title="Ошибка отправки заявки в 1С",
            message=export.error_message or "Не удалось отправить заявку в 1С",
            entity_type="document",
            entity_id=document.id,
            document_id=document.id,
            payload={"document_number": document.number, "error_code": export.error_code},
            dedupe=False,
            skip_self=False,
        )
