from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.cash_flow.allocation_repository import CashFlowAllocationRepository
from app.modules.cash_flow.mapping_repository import CashFlowMappingRepository
from app.modules.cash_flow.mapping_service import CashFlowMappingService
from app.modules.documents.models import Document, DocumentApprovalStatus
from app.modules.integration.log_repository import IntegrationLogRepository
from app.modules.integration.log_service import IntegrationLogService
from app.modules.integration.one_c.cash_flow_documents_schemas import (
    CashFlowDocumentImportItem,
    CashFlowDocumentsImportEnvelope,
    CashFlowDocumentsImportItemError,
    CashFlowDocumentsImportResult,
)

MAX_IMPORT_ITEMS = 1000

DOCUMENT_TYPE_MAP: dict[str, tuple[str, str]] = {
    "ПлатежноеПоручениеВходящее": ("PaymentOrderIncoming", "Inflow"),
    "ПриходныйКассовыйОрдер": ("CashReceiptOrder", "Inflow"),
    "ПлатежныйОрдерПоступлениеДенежныхСредств": ("MoneyReceiptOrder", "Inflow"),
    "ПлатежноеПоручениеИсходящее": ("PaymentOrderOutgoing", "Outflow"),
    "РасходныйКассовыйОрдер": ("CashExpenseOrder", "Outflow"),
    "ПлатежныйОрдерСписаниеДенежныхСредств": ("MoneyExpenseOrder", "Outflow"),
}
PROTECTED_MANUAL_FIELDS = {
    "cash_flow_item_id",
    "project_id",
    "cash_flow_operation_type_id",
    "management_comment",
}
CRITICAL_SOURCE_FIELDS = {
    "amount",
    "source_document_date",
    "currency_id",
    "cash_flow_direction",
    "organization_id",
    "counterparty_id",
    "contract_id",
}
ALLOCATION_COMPLETED_FIELDS = {"Completed", "Ignored"}


class CashFlowDocumentsImportService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(AuditRepository(db))
        self.log_service = IntegrationLogService(IntegrationLogRepository(db))
        self.mapping_service = CashFlowMappingService(CashFlowMappingRepository(db))
        self.repository = CashFlowAllocationRepository(db)

    def import_cash_flow_documents(
        self,
        payload: CashFlowDocumentsImportEnvelope,
        user_id: UUID,
    ) -> CashFlowDocumentsImportResult:
        started_at = perf_counter()
        result = CashFlowDocumentsImportResult(
            source_system=payload.source_system,
            received=len(payload.items),
            created=0,
            updated=0,
            skipped=0,
            completed=0,
            needs_enrichment=0,
            errors=[],
        )
        batch_id = str(uuid4())
        request_payload = payload.model_dump(mode="json")

        try:
            self._validate_batch_size(payload.items)
            doc_type, doc_version = self.repository.get_cash_flow_allocation_document_type_and_version()
            for index, raw_item in enumerate(payload.items):
                parsed = self._validate_item(index, raw_item, result)
                if parsed is None:
                    continue

                normalized_type, normalized_direction = self._resolve_type_and_direction(parsed)
                if normalized_type is None or normalized_direction is None:
                    self._append_error(
                        result,
                        index=index,
                        external_id=parsed.external_id,
                        code="UNSUPPORTED_CASH_FLOW_DOCUMENT_TYPE",
                        message="Unsupported 1C cash flow document type",
                        details={"source_document_type_1c": parsed.source_document_type_1c},
                    )
                    continue

                source_payload = self._build_source_payload(parsed, payload.source_system, normalized_type, normalized_direction)
                rule = self.mapping_service.find_rule_for_source(
                    source_system=payload.source_system,
                    source_document_type_1c=parsed.source_document_type_1c,
                    source_document_type_code=normalized_type,
                    cash_flow_direction=normalized_direction,
                )
                if rule is None:
                    self._append_error(
                        result,
                        index=index,
                        external_id=parsed.external_id,
                        code="CASH_FLOW_MAPPING_RULE_NOT_FOUND",
                        message="No active mapping rule found for 1C cash flow document",
                        details={"source_document_type_1c": parsed.source_document_type_1c},
                    )
                    continue

                mapping_result = self.mapping_service.apply_mapping_rule(rule.id, source_payload)
                if mapping_result.status == "Failed":
                    self._append_error(
                        result,
                        index=index,
                        external_id=parsed.external_id,
                        code="CASH_FLOW_MAPPING_FAILED",
                        message="Cash flow mapping failed",
                        details={"field_results": [item.model_dump(mode="json") for item in mapping_result.field_results]},
                    )
                    continue

                existing = self.repository.find_allocation_by_source_identity(
                    source_system=payload.source_system,
                    source_document_type_1c=parsed.source_document_type_1c,
                    source_document_external_id=parsed.external_id,
                )
                if existing is None:
                    document = self._create_document_from_import(
                        document_type_id=doc_type.id,
                        document_type_version_id=doc_version.id,
                        author_id=user_id,
                        batch_id=batch_id,
                        source_payload=source_payload,
                        mapping_result=mapping_result.model_dump(mode="json"),
                        mapped_data=mapping_result.mapped_data,
                    )
                    result.created += 1
                    self._count_status(result, document.data_json.get("allocation_status"))
                    self.audit_service.log(
                        "document",
                        document.id,
                        "cash_flow_allocation_created_from_1c",
                        user_id=user_id,
                        new_values_json={
                            "document_id": str(document.id),
                            "source_system": payload.source_system,
                            "source_document_type_1c": parsed.source_document_type_1c,
                            "source_document_external_id": parsed.external_id,
                            "allocation_status": document.data_json.get("allocation_status"),
                        },
                    )
                    self.audit_service.log(
                        "document",
                        document.id,
                        "cash_flow_allocation_imported",
                        user_id=user_id,
                        new_values_json={"import_batch_id": batch_id},
                    )
                else:
                    old_data = deepcopy(existing.data_json or {})
                    updated_document, source_changed = self._update_document_from_import(
                        existing=existing,
                        batch_id=batch_id,
                        source_payload=source_payload,
                        mapping_result=mapping_result.model_dump(mode="json"),
                        mapped_data=mapping_result.mapped_data,
                    )
                    result.updated += 1
                    self._count_status(result, updated_document.data_json.get("allocation_status"))
                    self.audit_service.log(
                        "document",
                        updated_document.id,
                        "cash_flow_allocation_updated_from_1c",
                        user_id=user_id,
                        old_values_json={"allocation_status": old_data.get("allocation_status"), "source_changed": old_data.get("source_changed")},
                        new_values_json={
                            "allocation_status": updated_document.data_json.get("allocation_status"),
                            "source_changed": updated_document.data_json.get("source_changed"),
                        },
                    )
                    self.audit_service.log(
                        "document",
                        updated_document.id,
                        "cash_flow_allocation_imported",
                        user_id=user_id,
                        new_values_json={"import_batch_id": batch_id},
                    )
                    if source_changed:
                        self.audit_service.log(
                            "document",
                            updated_document.id,
                            "cash_flow_allocation_source_changed",
                            user_id=user_id,
                            new_values_json={"source_changed": True},
                        )

            duration_ms = int((perf_counter() - started_at) * 1000)
            self.log_service.create_inbound_import_log(
                operation_type="1c_import_cash_flow_documents",
                request_url="/api/v1/integration/1c/cash-flow-documents/import",
                request_payload=request_payload,
                response_payload=result.model_dump(mode="json"),
                initiated_by=user_id,
                duration_ms=duration_ms,
                status="PartialSuccess" if result.errors or result.skipped else "Success",
            )
            self.db.commit()
            return result
        except AppError as exc:
            self.db.rollback()
            duration_ms = int((perf_counter() - started_at) * 1000)
            self.log_service.create_inbound_import_log(
                operation_type="1c_import_cash_flow_documents",
                request_url="/api/v1/integration/1c/cash-flow-documents/import",
                request_payload=request_payload,
                response_payload={},
                initiated_by=user_id,
                duration_ms=duration_ms,
                status="Failed",
                error_code=exc.code,
                error_message=exc.message,
                error_details=exc.details if isinstance(exc.details, dict) else {},
            )
            self.db.commit()
            raise

    def _validate_batch_size(self, items: list[dict]) -> None:
        if len(items) > MAX_IMPORT_ITEMS:
            raise AppError(
                "Import batch contains more than 1000 items",
                code="IMPORT_BATCH_TOO_LARGE",
                status_code=422,
            )

    def _validate_item(
        self,
        index: int,
        raw_item: dict,
        result: CashFlowDocumentsImportResult,
    ) -> CashFlowDocumentImportItem | None:
        try:
            return CashFlowDocumentImportItem.model_validate(raw_item)
        except Exception as exc:
            message = str(exc).splitlines()[0]
            self._append_error(
                result,
                index=index,
                external_id=raw_item.get("external_id") if isinstance(raw_item, dict) else None,
                code="VALIDATION_ERROR",
                message=message,
            )
            return None

    def _resolve_type_and_direction(self, item: CashFlowDocumentImportItem) -> tuple[str | None, str | None]:
        resolved = DOCUMENT_TYPE_MAP.get(item.source_document_type_1c)
        payload_type = item.source_document_type
        payload_direction = item.cash_flow_direction
        if resolved is None and (payload_type is None or payload_direction is None):
            return None, None
        resolved_type = payload_type or (resolved[0] if resolved else None)
        resolved_direction = payload_direction or (resolved[1] if resolved else None)
        return resolved_type, resolved_direction

    def _build_source_payload(
        self,
        item: CashFlowDocumentImportItem,
        source_system: str,
        source_document_type: str,
        cash_flow_direction: str,
    ) -> dict:
        payload = item.model_dump(mode="json")
        payload["source_system"] = source_system
        payload["source_document_type"] = source_document_type
        payload["cash_flow_direction"] = cash_flow_direction
        payload["ref"] = item.external_id
        return payload

    def _create_document_from_import(
        self,
        *,
        document_type_id,
        document_type_version_id,
        author_id: UUID,
        batch_id: str,
        source_payload: dict,
        mapping_result: dict,
        mapped_data: dict,
    ) -> Document:
        data_json = self._compose_allocation_data(
            previous=None,
            source_payload=source_payload,
            mapping_result=mapping_result,
            mapped_data=mapped_data,
            batch_id=batch_id,
        )
        document = self.repository.create_cash_flow_allocation_document(
            document_type_id=document_type_id,
            document_type_version_id=document_type_version_id,
            author_id=author_id,
            number=self.repository.generate_document_number(prefix="CFA"),
            title=self._allocation_title(data_json),
            document_date=self._document_date_from_payload(data_json),
            data_json=data_json,
        )
        return document

    def _update_document_from_import(
        self,
        *,
        existing: Document,
        batch_id: str,
        source_payload: dict,
        mapping_result: dict,
        mapped_data: dict,
    ) -> tuple[Document, bool]:
        previous = deepcopy(existing.data_json or {})
        source_changed = self._compute_source_changed(previous, mapped_data)
        data_json = self._compose_allocation_data(
            previous=previous,
            source_payload=source_payload,
            mapping_result=mapping_result,
            mapped_data=mapped_data,
            batch_id=batch_id,
        )
        if previous.get("allocation_status") in ALLOCATION_COMPLETED_FIELDS:
            data_json["allocation_status"] = previous.get("allocation_status")
        data_json["source_changed"] = bool(previous.get("source_changed")) or source_changed
        existing.data_json = data_json
        existing.title = self._allocation_title(data_json)
        existing.document_date = self._document_date_from_payload(data_json)
        self.repository.save_document(existing)
        return existing, source_changed

    def _compose_allocation_data(
        self,
        *,
        previous: dict | None,
        source_payload: dict,
        mapping_result: dict,
        mapped_data: dict,
        batch_id: str,
    ) -> dict:
        previous = previous or {}
        data_json = deepcopy(previous)

        source_fields = {
            "source_system": source_payload.get("source_system"),
            "source_document_external_id": source_payload.get("external_id"),
            "source_document_type": source_payload.get("source_document_type"),
            "source_document_type_1c": source_payload.get("source_document_type_1c"),
            "source_document_number": source_payload.get("number"),
            "source_document_date": source_payload.get("date"),
            "source_document_posted_at": source_payload.get("posted_at"),
            "source_document_amount": source_payload.get("amount"),
            "source_document_currency_id": mapped_data.get("currency_id"),
            "source_document_purpose": source_payload.get("payment_purpose"),
            "source_document_comment": source_payload.get("comment"),
            "raw_source_payload": source_payload,
            "import_batch_id": batch_id,
            "mapping_rule_id": str(mapping_result.get("rule_id") or mapped_data.get("mapping_rule_id") or ""),
            "mapping_result": mapping_result.get("status"),
            "missing_required_fields": mapped_data.get("missing_required_fields", []),
        }
        data_json.update(source_fields)

        for field_name, value in mapped_data.items():
            if field_name in {"mapping_rule_id", "mapping_result", "missing_required_fields"}:
                continue
            if field_name in PROTECTED_MANUAL_FIELDS and previous.get(field_name) not in (None, "", [], {}):
                continue
            if field_name == "allocation_status" and previous.get("allocation_status") in ALLOCATION_COMPLETED_FIELDS:
                continue
            data_json[field_name] = value

        data_json["source_changed"] = bool(previous.get("source_changed", False))
        return data_json

    def _compute_source_changed(self, previous: dict, mapped_data: dict) -> bool:
        if previous.get("allocation_status") not in ALLOCATION_COMPLETED_FIELDS:
            return False
        for field_name in CRITICAL_SOURCE_FIELDS:
            if self._normalize_compare(previous.get(field_name)) != self._normalize_compare(mapped_data.get(field_name)):
                return True
        return False

    def _normalize_compare(self, value):
        if isinstance(value, Decimal):
            return str(value)
        return value

    def _count_status(self, result: CashFlowDocumentsImportResult, allocation_status: str | None) -> None:
        if allocation_status == "Completed":
            result.completed += 1
        elif allocation_status == "NeedsEnrichment":
            result.needs_enrichment += 1

    def _allocation_title(self, data_json: dict) -> str:
        return f"Разноска БДДС {data_json.get('source_document_number') or data_json.get('source_document_external_id') or ''}".strip()

    def _document_date_from_payload(self, data_json: dict) -> datetime:
        raw_value = data_json.get("source_document_date")
        if isinstance(raw_value, str):
            return datetime.fromisoformat(f"{raw_value}T00:00:00+00:00")
        return datetime.now(timezone.utc)

    def _append_error(
        self,
        result: CashFlowDocumentsImportResult,
        *,
        index: int,
        external_id: str | None,
        code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        result.errors.append(
            CashFlowDocumentsImportItemError(
                index=index,
                external_id=external_id,
                code=code,
                message=message,
                details=details,
            )
        )
        result.skipped += 1
