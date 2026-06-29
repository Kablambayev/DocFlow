from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import status

from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.documents.models import DocumentApprovalStatus
from app.modules.integration.log_repository import IntegrationLogRepository
from app.modules.integration.log_service import IntegrationLogService
from app.modules.integration.one_c.outbound_client import OneCOutboundClient
from app.modules.integration.one_c.outbound_service import OneCOutboundService
from app.modules.integration.one_c.payment_export_models import PaymentRequest1CExportStatus
from app.modules.integration.one_c.payment_export_repository import PaymentRequest1CExportRepository
from app.modules.payment_registers.models import PaymentRegisterRow, PaymentRegisterStatus
from app.modules.payment_registers.repository import PaymentRegisterRepository
from app.modules.payment_registers.schemas import (
    PaymentRegisterActionResponse,
    PaymentRegisterAvailableRequestRead,
    PaymentRegisterAvailableRequestsResponse,
    PaymentRegisterCreate,
    PaymentRegisterDetailRead,
    PaymentRegisterDocumentLookupItem,
    PaymentRegisterListItem,
    PaymentRegisterLookupItem,
    PaymentRegisterRowAddError,
    PaymentRegisterRowExportInfo,
    PaymentRegisterRowRead,
    PaymentRegisterRowsAddRequest,
    PaymentRegisterRowsAddResponse,
    PaymentRegisterSendResponse,
    PaymentRegisterSendRowResult,
    PaymentRegisterUpdate,
    PaymentRegistersResponse,
)
from app.modules.treasury.repository import TreasuryRepository


ACTIVE_REGISTER_STATUSES = [
    PaymentRegisterStatus.DRAFT,
    PaymentRegisterStatus.READY_TO_SEND,
    PaymentRegisterStatus.SENDING,
    PaymentRegisterStatus.PARTIALLY_SENT,
]
REGISTER_SUCCESS_EXPORT_STATUSES = {
    PaymentRequest1CExportStatus.CREATED_IN_1C,
    PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C,
}


class PaymentRegisterService:
    def __init__(self, repository: PaymentRegisterRepository):
        self.repository = repository
        self.treasury_repository = TreasuryRepository(repository.db)
        self.audit_service = AuditService(AuditRepository(repository.db))
        self.log_service = IntegrationLogService(IntegrationLogRepository(repository.db))
        self.outbound_service = OneCOutboundService(PaymentRequest1CExportRepository(repository.db), OneCOutboundClient())

    def list_registers(
        self,
        *,
        current_user,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        organization_id: UUID | None,
        currency_id: UUID | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PaymentRegistersResponse:
        self._require_permission(current_user.id, "payment_register.read")
        items, total = self.repository.list_registers(
            status=status,
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id,
            currency_id=currency_id,
            search=search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PaymentRegistersResponse(
            items=[self._build_register_list_item(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def create_register(self, payload: PaymentRegisterCreate, current_user) -> PaymentRegisterDetailRead:
        self._require_permission(current_user.id, "payment_register.manage")
        register = self.repository.create_register(
            number=(payload.number or self._generate_number()).strip(),
            date=payload.date,
            status=PaymentRegisterStatus.DRAFT,
            organization_id=payload.organization_id,
            currency_id=payload.currency_id,
            comment=payload.comment,
            created_by=current_user.id,
            total_amount=Decimal("0.00"),
            rows_count=0,
            sent_rows_count=0,
            failed_rows_count=0,
        )
        self.audit_service.log(
            "payment_register",
            register.id,
            "payment_register_created",
            user_id=current_user.id,
            new_values_json={"number": register.number, "status": register.status},
        )
        self.repository.db.commit()
        return self.get_register(register.id, current_user)

    def get_register(self, register_id: UUID, current_user) -> PaymentRegisterDetailRead:
        self._require_permission(current_user.id, "payment_register.read")
        register = self._require_register(register_id)
        return self._build_register_detail(register)

    def update_register(self, register_id: UUID, payload: PaymentRegisterUpdate, current_user) -> PaymentRegisterDetailRead:
        self._require_permission(current_user.id, "payment_register.manage")
        register = self._require_register(register_id)
        self._ensure_status(register.status, {PaymentRegisterStatus.DRAFT}, "REGISTER_EDIT_NOT_ALLOWED")
        old_values = self._register_snapshot(register)
        values = payload.model_dump(exclude_unset=True)
        if "number" in values:
            values["number"] = (values["number"] or self._generate_number()).strip()
        for key, value in values.items():
            setattr(register, key, value)
        self.repository.save_register(register)
        self._recalculate_register(register)
        self.audit_service.log(
            "payment_register",
            register.id,
            "payment_register_updated",
            user_id=current_user.id,
            old_values_json=old_values,
            new_values_json=self._register_snapshot(register),
        )
        self.repository.db.commit()
        return self.get_register(register.id, current_user)

    def delete_register(self, register_id: UUID, current_user) -> None:
        self._require_permission(current_user.id, "payment_register.manage")
        register = self._require_register(register_id)
        self._ensure_status(register.status, {PaymentRegisterStatus.DRAFT}, "REGISTER_DELETE_NOT_ALLOWED")
        self.repository.delete_register(register)
        self.audit_service.log("payment_register", register_id, "payment_register_deleted", user_id=current_user.id)
        self.repository.db.commit()

    def list_available_payment_requests(
        self,
        *,
        current_user,
        organization_id: UUID | None,
        currency_id: UUID | None,
        search: str | None,
        include_failed_exports: bool,
        limit: int,
        offset: int,
    ) -> PaymentRegisterAvailableRequestsResponse:
        self._require_permission(current_user.id, "payment_register.read")
        documents = self.repository.list_payment_request_documents()
        document_ids = [item.id for item in documents]
        exports = self.repository.get_exports_by_document_ids(document_ids)
        active_memberships = self.repository.get_active_register_memberships(
            document_ids,
            active_statuses=[item.value for item in ACTIVE_REGISTER_STATUSES],
        )
        approved_dates = self.treasury_repository.get_approved_at_by_document_ids(documents)
        type_codes = self.repository.get_document_type_codes({item.document_type_id for item in documents})
        items = []
        for document in documents:
            export = exports.get(document.id)
            if not self._is_document_available_for_register(
                document=document,
                document_type_code=type_codes.get(document.document_type_id),
                export=export,
                active_memberships=active_memberships,
                include_failed_exports=include_failed_exports,
            ):
                continue
            item = self._build_available_document_item(document, export, approved_dates.get(document.id))
            if organization_id is not None and (item.organization is None or item.organization.id != organization_id):
                continue
            if currency_id is not None and (item.currency is None or item.currency.id != currency_id):
                continue
            if search:
                needle = search.strip().lower()
                if needle and needle not in (item.number or "").lower() and needle not in (item.title or "").lower():
                    continue
            items.append(item)
        total = len(items)
        return PaymentRegisterAvailableRequestsResponse(items=items[offset : offset + limit], total=total, limit=limit, offset=offset)

    def add_rows(self, register_id: UUID, payload: PaymentRegisterRowsAddRequest, current_user) -> PaymentRegisterRowsAddResponse:
        self._require_permission(current_user.id, "payment_register.manage")
        register = self._require_register(register_id)
        self._ensure_status(register.status, {PaymentRegisterStatus.DRAFT}, "REGISTER_ADD_ROWS_NOT_ALLOWED")
        document_ids = list(dict.fromkeys(payload.document_ids))
        documents = self.repository.get_documents_by_ids(document_ids)
        exports = self.repository.get_exports_by_document_ids(document_ids)
        active_memberships = self.repository.get_active_register_memberships(
            document_ids,
            active_statuses=[item.value for item in ACTIVE_REGISTER_STATUSES],
            exclude_register_id=register.id,
        )
        type_codes = self.repository.get_document_type_codes({item.document_type_id for item in documents.values()})
        existing_document_ids = {row.document_id for row in self.repository.list_rows(register.id)}
        next_row_number = self.repository.get_max_row_number(register.id)
        added_count = 0
        skipped_document_ids: list[UUID] = []
        errors: list[PaymentRegisterRowAddError] = []

        for document_id in document_ids:
            document = documents.get(document_id)
            if document is None:
                errors.append(PaymentRegisterRowAddError(document_id=document_id, code="DOCUMENT_NOT_FOUND", message="Document not found"))
                continue
            if document_id in existing_document_ids:
                skipped_document_ids.append(document_id)
                continue
            export = exports.get(document_id)
            if not self._is_document_available_for_register(
                document=document,
                document_type_code=type_codes.get(document.document_type_id),
                export=export,
                active_memberships=active_memberships,
                include_failed_exports=True,
            ):
                code, message = self._document_unavailable_error(document, export, active_memberships.get(document_id), type_codes.get(document.document_type_id))
                errors.append(PaymentRegisterRowAddError(document_id=document_id, code=code, message=message))
                continue
            row_payload = self._document_row_payload(document)
            next_row_number += 1
            row = self.repository.create_row(
                register_id=register.id,
                document_id=document.id,
                row_number=next_row_number,
                **row_payload,
            )
            if export is not None:
                self._apply_export_to_row(row, export)
            self.audit_service.log(
                "payment_register",
                register.id,
                "payment_register_row_added",
                user_id=current_user.id,
                new_values_json={"row_id": str(row.id), "document_id": str(document.id), "row_number": row.row_number},
            )
            added_count += 1

        self._recalculate_register(register)
        self.repository.db.commit()
        return PaymentRegisterRowsAddResponse(
            payment_register=self.get_register(register.id, current_user),
            added_count=added_count,
            skipped_document_ids=skipped_document_ids,
            errors=errors,
        )

    def remove_row(self, register_id: UUID, row_id: UUID, current_user) -> PaymentRegisterDetailRead:
        self._require_permission(current_user.id, "payment_register.manage")
        register = self._require_register(register_id)
        self._ensure_status(register.status, {PaymentRegisterStatus.DRAFT}, "REGISTER_REMOVE_ROW_NOT_ALLOWED")
        row = self.repository.get_row(row_id)
        if row is None or row.register_id != register.id:
            raise AppError("Register row not found", code="PAYMENT_REGISTER_ROW_NOT_FOUND", status_code=404)
        self.repository.delete_row(row)
        self._renumber_rows(register.id)
        self._recalculate_register(register)
        self.audit_service.log(
            "payment_register",
            register.id,
            "payment_register_row_removed",
            user_id=current_user.id,
            old_values_json={"row_id": str(row.id), "document_id": str(row.document_id)},
        )
        self.repository.db.commit()
        return self.get_register(register.id, current_user)

    def mark_ready(self, register_id: UUID, current_user) -> PaymentRegisterActionResponse:
        self._require_permission(current_user.id, "payment_register.manage")
        register = self._require_register(register_id)
        self._ensure_status(register.status, {PaymentRegisterStatus.DRAFT}, "REGISTER_MARK_READY_NOT_ALLOWED")
        rows = self.repository.list_rows(register.id)
        if not rows:
            raise AppError("Register must contain at least one row", code="PAYMENT_REGISTER_EMPTY", status_code=409)
        validation_errors = self._validate_register_rows(rows)
        if validation_errors:
            raise AppError(
                "Register contains invalid rows",
                code="PAYMENT_REGISTER_ROWS_INVALID",
                status_code=409,
                details=validation_errors,
            )
        register.status = PaymentRegisterStatus.READY_TO_SEND
        self.repository.save_register(register)
        self.audit_service.log("payment_register", register.id, "payment_register_marked_ready", user_id=current_user.id)
        self.repository.db.commit()
        return PaymentRegisterActionResponse(payment_register=self.get_register(register.id, current_user))

    def send_to_1c(self, register_id: UUID, current_user, *, force: bool) -> PaymentRegisterSendResponse:
        self._require_permission(current_user.id, "payment_register.send")
        register = self._require_register(register_id)
        self._ensure_status(
            register.status,
            {PaymentRegisterStatus.READY_TO_SEND, PaymentRegisterStatus.PARTIALLY_SENT, PaymentRegisterStatus.FAILED},
            "REGISTER_SEND_NOT_ALLOWED",
        )
        rows = self.repository.list_rows(register.id)
        if not rows:
            raise AppError("Register must contain at least one row", code="PAYMENT_REGISTER_EMPTY", status_code=409)

        started_at = perf_counter()
        register.status = PaymentRegisterStatus.SENDING
        register.sent_by = current_user.id
        register.sent_at = datetime.now(timezone.utc)
        self.repository.save_register(register)
        correlation_id = str(uuid4())
        operation_log = self.log_service.create_outbound_http_log(
            operation_type="1c_export_payment_register",
            entity_type="payment_register",
            entity_id=register.id,
            initiated_by=current_user.id,
            request_url="internal://payment-register/send-to-1c",
            request_method="POST",
            request_payload={
                "register_id": str(register.id),
                "register_number": register.number,
                "force": force,
                "document_ids": [str(row.document_id) for row in rows],
            },
            correlation_id=correlation_id,
            idempotency_key=str(register.id),
        )
        self.audit_service.log("payment_register", register.id, "payment_register_send_started", user_id=current_user.id)
        self.repository.db.commit()

        results: list[PaymentRegisterSendRowResult] = []
        skipped_rows_count = 0
        processed_rows_count = 0

        for row in rows:
            if not force and row.export_status in REGISTER_SUCCESS_EXPORT_STATUSES:
                skipped_rows_count += 1
                results.append(PaymentRegisterSendRowResult(row_id=row.id, document_id=row.document_id, export_status=row.export_status))
                continue
            try:
                processed_rows_count += 1
                result = self.outbound_service.send_approved_payment_request_to_1c(row.document_id, current_user, force=force)
                export = self.outbound_service.repository.get_by_document_id(row.document_id)
                if result.status == "already_exported" and export is None:
                    export = self.outbound_service.repository.get_by_document_id(row.document_id)
                if export is not None:
                    self._apply_export_to_row(row, export)
                else:
                    row.export_status = "Failed"
                    row.error_code = "EXPORT_RESULT_NOT_FOUND"
                    row.error_message = "Export result not found"
                self.repository.save_row(row)
                results.append(
                    PaymentRegisterSendRowResult(
                        row_id=row.id,
                        document_id=row.document_id,
                        export_status=row.export_status,
                        error_code=row.error_code,
                        error_message=row.error_message,
                    )
                )
            except AppError as exc:
                row.export_status = PaymentRequest1CExportStatus.FAILED
                row.export_id = None
                row.one_c_payment_order_external_id = None
                row.one_c_payment_order_number = None
                row.one_c_payment_order_date = None
                row.error_code = exc.code
                row.error_message = exc.message
                self.repository.save_row(row)
                self.repository.db.commit()
                results.append(
                    PaymentRegisterSendRowResult(
                        row_id=row.id,
                        document_id=row.document_id,
                        export_status=row.export_status,
                        error_code=row.error_code,
                        error_message=row.error_message,
                    )
                )

        self._recalculate_register(register)
        if register.rows_count > 0 and register.sent_rows_count == register.rows_count:
            register.status = PaymentRegisterStatus.SENT
            final_audit_action = "payment_register_sent"
            final_log_method = self.log_service.mark_success
        elif register.sent_rows_count > 0:
            register.status = PaymentRegisterStatus.PARTIALLY_SENT
            final_audit_action = "payment_register_partially_sent"
            final_log_method = self.log_service.mark_partial_success
        else:
            register.status = PaymentRegisterStatus.FAILED
            final_audit_action = "payment_register_failed"
            final_log_method = self.log_service.mark_failed
        self.repository.save_register(register)
        duration_ms = int((perf_counter() - started_at) * 1000)
        log_payload = {
            "register_id": str(register.id),
            "register_status": register.status,
            "processed_rows_count": processed_rows_count,
            "skipped_rows_count": skipped_rows_count,
            "sent_rows_count": register.sent_rows_count,
            "failed_rows_count": register.failed_rows_count,
            "results": [item.model_dump(mode="json") for item in results],
        }
        if final_log_method == self.log_service.mark_failed:
            final_log_method(
                operation_log.id,
                response_payload=log_payload,
                error_code="PAYMENT_REGISTER_EXPORT_FAILED",
                error_message="All register rows failed to export",
                duration_ms=duration_ms,
            )
        else:
            final_log_method(operation_log.id, response_payload=log_payload, duration_ms=duration_ms)
        self.audit_service.log(
            "payment_register",
            register.id,
            final_audit_action,
            user_id=current_user.id,
            new_values_json={
                "status": register.status,
                "sent_rows_count": register.sent_rows_count,
                "failed_rows_count": register.failed_rows_count,
            },
        )
        self.repository.db.commit()
        return PaymentRegisterSendResponse(
            payment_register=self.get_register(register.id, current_user),
            processed_rows_count=processed_rows_count,
            skipped_rows_count=skipped_rows_count,
            results=results,
        )

    def cancel(self, register_id: UUID, current_user) -> PaymentRegisterActionResponse:
        self._require_permission(current_user.id, "payment_register.manage")
        register = self._require_register(register_id)
        self._ensure_status(
            register.status,
            {
                PaymentRegisterStatus.DRAFT,
                PaymentRegisterStatus.READY_TO_SEND,
                PaymentRegisterStatus.FAILED,
                PaymentRegisterStatus.PARTIALLY_SENT,
            },
            "REGISTER_CANCEL_NOT_ALLOWED",
        )
        register.status = PaymentRegisterStatus.CANCELLED
        self.repository.save_register(register)
        self.audit_service.log("payment_register", register.id, "payment_register_cancelled", user_id=current_user.id)
        self.repository.db.commit()
        return PaymentRegisterActionResponse(payment_register=self.get_register(register.id, current_user))

    def _build_register_list_item(self, register) -> PaymentRegisterListItem:
        return PaymentRegisterListItem(
            id=register.id,
            number=register.number,
            date=register.date,
            status=register.status,
            organization=self._lookup(self.repository.get_organization(register.organization_id)),
            currency=self._lookup(self.repository.get_currency(register.currency_id)),
            comment=register.comment,
            created_by=self._lookup(self.repository.get_user(register.created_by)),
            sent_by=self._lookup(self.repository.get_user(register.sent_by)),
            sent_at=register.sent_at,
            total_amount=register.total_amount,
            rows_count=register.rows_count,
            sent_rows_count=register.sent_rows_count,
            failed_rows_count=register.failed_rows_count,
            created_at=register.created_at,
            updated_at=register.updated_at,
        )

    def _build_register_detail(self, register) -> PaymentRegisterDetailRead:
        rows = self.repository.list_rows(register.id)
        return PaymentRegisterDetailRead(**self._build_register_list_item(register).model_dump(), rows=[self._build_row_read(row) for row in rows])

    def _build_row_read(self, row: PaymentRegisterRow) -> PaymentRegisterRowRead:
        document = self.repository.get_documents_by_ids([row.document_id]).get(row.document_id)
        contract = self.repository.get_contract(row.contract_id)
        return PaymentRegisterRowRead(
            id=row.id,
            register_id=row.register_id,
            document_id=row.document_id,
            row_number=row.row_number,
            amount=row.amount,
            payment_purpose=row.payment_purpose,
            organization=self._lookup(self.repository.get_organization(row.organization_id)),
            counterparty=self._lookup(self.repository.get_counterparty(row.counterparty_id)),
            contract=self._contract_lookup(contract),
            currency=self._lookup(self.repository.get_currency(row.currency_id)),
            project=self._lookup(self.repository.get_project(row.project_id)),
            expense_item=self._lookup(self.repository.get_expense_item(row.expense_item_id)),
            document_number=document.number if document is not None else None,
            document_title=document.title if document is not None else None,
            document_date=document.document_date if document is not None else None,
            approval_status=document.approval_status if document is not None else None,
            export=PaymentRegisterRowExportInfo(
                status=row.export_status,
                export_id=row.export_id,
                one_c_payment_order_external_id=row.one_c_payment_order_external_id,
                one_c_payment_order_number=row.one_c_payment_order_number,
                one_c_payment_order_date=row.one_c_payment_order_date,
                error_code=row.error_code,
                error_message=row.error_message,
            ),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _build_available_document_item(self, document, export, approved_at: datetime | None) -> PaymentRegisterAvailableRequestRead:
        data = document.data_json or {}
        organization = self.repository.get_organization(self.treasury_repository.parse_uuid(data.get("organization_id")))
        counterparty = self.repository.get_counterparty(self.treasury_repository.parse_uuid(data.get("counterparty_id")))
        contract = self.repository.get_contract(self.treasury_repository.parse_uuid(data.get("contract_id")))
        currency = self.repository.get_currency(self.treasury_repository.parse_uuid(data.get("currency_id")))
        project = self.repository.get_project(self.treasury_repository.parse_uuid(data.get("project_id")))
        expense_item = self.repository.get_expense_item(self.treasury_repository.parse_uuid(data.get("expense_item_id")))
        return PaymentRegisterAvailableRequestRead(
            document_id=document.id,
            number=document.number,
            title=document.title,
            document_date=document.document_date,
            approved_at=approved_at or document.updated_at,
            organization=self._lookup(organization),
            counterparty=self._lookup(counterparty),
            contract=self._contract_lookup(contract),
            currency=self._lookup(currency),
            project=self._lookup(project),
            expense_item=self._lookup(expense_item),
            amount=self.treasury_repository.parse_decimal(data.get("amount")),
            payment_purpose=data.get("payment_purpose") or data.get("paymentPurpose"),
            export_status=export.status if export is not None else None,
            export_error_code=export.error_code if export is not None else None,
            export_error_message=export.error_message if export is not None else None,
        )

    def _is_document_available_for_register(self, *, document, document_type_code: str | None, export, active_memberships, include_failed_exports: bool) -> bool:
        if document_type_code != "PaymentRequest":
            return False
        if document.approval_status != DocumentApprovalStatus.APPROVED:
            return False
        if document.approval_status == DocumentApprovalStatus.ARCHIVED:
            return False
        if document.id in active_memberships:
            return False
        if export is None:
            return True
        if export.status in REGISTER_SUCCESS_EXPORT_STATUSES:
            return False
        if export.status == PaymentRequest1CExportStatus.FAILED:
            return include_failed_exports
        return True

    def _document_unavailable_error(self, document, export, active_membership, document_type_code: str | None) -> tuple[str, str]:
        if document_type_code != "PaymentRequest":
            return "UNSUPPORTED_DOCUMENT_TYPE", "Only PaymentRequest can be added"
        if document.approval_status != DocumentApprovalStatus.APPROVED:
            return "DOCUMENT_NOT_APPROVED", "Only approved payment requests can be added"
        if active_membership is not None:
            return "PAYMENT_REQUEST_ALREADY_IN_ACTIVE_REGISTER", "Payment request already belongs to an active register"
        if export is not None and export.status in REGISTER_SUCCESS_EXPORT_STATUSES:
            return "PAYMENT_REQUEST_ALREADY_EXPORTED", "Payment request is already exported to 1C"
        if export is not None and export.status == PaymentRequest1CExportStatus.FAILED:
            return "PAYMENT_REQUEST_EXPORT_FAILED", "Payment request has failed export history"
        return "PAYMENT_REQUEST_NOT_AVAILABLE", "Payment request is not available for register"

    def _validate_register_rows(self, rows: list[PaymentRegisterRow]) -> list[dict[str, str]]:
        documents = self.repository.get_documents_by_ids([row.document_id for row in rows])
        type_codes = self.repository.get_document_type_codes({item.document_type_id for item in documents.values()})
        errors: list[dict[str, str]] = []
        for row in rows:
            document = documents.get(row.document_id)
            if document is None:
                errors.append({"row_id": str(row.id), "code": "DOCUMENT_NOT_FOUND"})
                continue
            document_type_code = type_codes.get(document.document_type_id)
            if document_type_code != "PaymentRequest":
                errors.append({"row_id": str(row.id), "code": "UNSUPPORTED_DOCUMENT_TYPE"})
            elif document.approval_status != DocumentApprovalStatus.APPROVED:
                errors.append({"row_id": str(row.id), "code": "DOCUMENT_NOT_APPROVED"})
        return errors

    def _document_row_payload(self, document) -> dict:
        data = document.data_json or {}
        amount = self.treasury_repository.parse_decimal(data.get("amount")) or Decimal("0.00")
        return {
            "organization_id": self.treasury_repository.parse_uuid(data.get("organization_id")),
            "counterparty_id": self.treasury_repository.parse_uuid(data.get("counterparty_id")),
            "contract_id": self.treasury_repository.parse_uuid(data.get("contract_id")),
            "currency_id": self.treasury_repository.parse_uuid(data.get("currency_id")),
            "project_id": self.treasury_repository.parse_uuid(data.get("project_id")),
            "expense_item_id": self.treasury_repository.parse_uuid(data.get("expense_item_id")),
            "amount": amount,
            "payment_purpose": data.get("payment_purpose") or data.get("paymentPurpose"),
            "export_status": None,
            "export_id": None,
            "one_c_payment_order_external_id": None,
            "one_c_payment_order_number": None,
            "one_c_payment_order_date": None,
            "error_code": None,
            "error_message": None,
        }

    def _recalculate_register(self, register) -> None:
        rows = self.repository.list_rows(register.id)
        register.rows_count = len(rows)
        register.total_amount = sum((row.amount or Decimal("0.00")) for row in rows) if rows else Decimal("0.00")
        register.sent_rows_count = sum(1 for row in rows if row.export_status in REGISTER_SUCCESS_EXPORT_STATUSES)
        register.failed_rows_count = sum(1 for row in rows if row.export_status == PaymentRequest1CExportStatus.FAILED)
        self.repository.save_register(register)

    def _renumber_rows(self, register_id: UUID) -> None:
        for index, row in enumerate(self.repository.list_rows(register_id), start=1):
            row.row_number = index
            self.repository.save_row(row)

    def _generate_number(self) -> str:
        max_number = 0
        for number in self.repository.list_register_numbers():
            suffix = number.removeprefix("REG-")
            if suffix.isdigit():
                max_number = max(max_number, int(suffix))
        return f"REG-{max_number + 1:06d}"

    def _apply_export_to_row(self, row, export) -> None:
        row.export_status = export.status
        row.export_id = export.id
        row.one_c_payment_order_external_id = export.one_c_payment_order_external_id
        row.one_c_payment_order_number = export.one_c_payment_order_number
        row.one_c_payment_order_date = export.one_c_payment_order_date
        row.error_code = export.error_code
        row.error_message = export.error_message

    def _require_register(self, register_id: UUID):
        register = self.repository.get_register(register_id)
        if register is None:
            raise AppError("Payment register not found", code="PAYMENT_REGISTER_NOT_FOUND", status_code=404)
        return register

    def _lookup(self, item) -> PaymentRegisterLookupItem | None:
        if item is None:
            return None
        code = getattr(item, "code", None)
        full_name = getattr(item, "full_name", None)
        return PaymentRegisterLookupItem(id=item.id, name=full_name or item.name, code=code)

    def _contract_lookup(self, item) -> PaymentRegisterDocumentLookupItem | None:
        if item is None:
            return None
        return PaymentRegisterDocumentLookupItem(
            id=item.id,
            name=item.name,
            code=item.code,
            number=getattr(item, "number", None),
        )

    def _register_snapshot(self, register) -> dict[str, str | None]:
        return {
            "number": register.number,
            "date": register.date.isoformat() if register.date else None,
            "status": register.status,
            "comment": register.comment,
        }

    def _ensure_status(self, current_status: str, allowed_statuses: set[str], error_code: str) -> None:
        if current_status not in allowed_statuses:
            raise AppError("Operation is not allowed for current register status", code=error_code, status_code=409)

    def _require_permission(self, user_id: UUID, permission_code: str) -> None:
        permissions = get_user_permission_codes(self.repository.db, user_id)
        if "admin.access" in permissions or permission_code in permissions:
            return
        raise AppError(
            "Permission required",
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"permission": permission_code},
        )
