from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.core.security import get_user_permission_codes
from app.modules.integration.log_repository import IntegrationLogRepository
from app.modules.integration.log_schemas import IntegrationLogDetail, IntegrationLogListItem, IntegrationLogsResponse

SENSITIVE_KEYS = {
    "authorization",
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "cookie",
    "set-cookie",
}


def mask_sensitive_data(value: Any):
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
                result[key] = "***MASKED***"
            else:
                result[key] = mask_sensitive_data(item)
        return result
    if isinstance(value, list):
        return [mask_sensitive_data(item) for item in value]
    return value


class IntegrationLogService:
    def __init__(self, repository: IntegrationLogRepository):
        self.repository = repository

    def create_started_log(
        self,
        *,
        direction: str,
        operation_type: str,
        status: str = "Started",
        integration_system: str = "1C",
        document_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        initiated_by: UUID | None = None,
        request_url: str | None = None,
        request_method: str | None = None,
        request_headers: dict[str, Any] | None = None,
        request_payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
    ):
        return self.repository.create(
            direction=direction,
            integration_system=integration_system,
            operation_type=operation_type,
            status=status,
            document_id=document_id,
            entity_type=entity_type,
            entity_id=entity_id,
            initiated_by=initiated_by,
            request_url=request_url,
            request_method=request_method,
            request_headers=mask_sensitive_data(request_headers or {}),
            request_payload=mask_sensitive_data(request_payload or {}),
            response_headers={},
            response_payload={},
            error_details={},
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )

    def mark_success(
        self,
        log_id: UUID,
        *,
        response_status_code: int | None = None,
        response_headers: dict[str, Any] | None = None,
        response_payload: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        status: str = "Success",
    ):
        log = self._require_log(log_id)
        log.status = status
        log.response_status_code = response_status_code
        log.response_headers = mask_sensitive_data(response_headers or {})
        log.response_payload = mask_sensitive_data(response_payload or {})
        log.duration_ms = duration_ms
        log.error_code = None
        log.error_message = None
        log.error_details = {}
        log.updated_at = datetime.now(timezone.utc)
        self.repository.save(log)
        return log

    def mark_partial_success(self, log_id: UUID, **kwargs):
        return self.mark_success(log_id, status="PartialSuccess", **kwargs)

    def mark_failed(
        self,
        log_id: UUID,
        *,
        response_status_code: int | None = None,
        response_headers: dict[str, Any] | None = None,
        response_payload: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        error_details: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        status: str = "Failed",
    ):
        log = self._require_log(log_id)
        log.status = status
        log.response_status_code = response_status_code
        log.response_headers = mask_sensitive_data(response_headers or {})
        log.response_payload = mask_sensitive_data(response_payload or {})
        log.error_code = error_code
        log.error_message = error_message
        log.error_details = mask_sensitive_data(error_details or {})
        log.duration_ms = duration_ms
        log.updated_at = datetime.now(timezone.utc)
        self.repository.save(log)
        return log

    def create_inbound_import_log(
        self,
        *,
        operation_type: str,
        request_url: str,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        initiated_by: UUID,
        duration_ms: int,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        error_details: dict[str, Any] | None = None,
    ):
        return self.repository.create(
            direction="Inbound",
            integration_system="1C",
            operation_type=operation_type,
            status=status,
            initiated_by=initiated_by,
            request_url=request_url,
            request_method="POST",
            request_headers={},
            request_payload=mask_sensitive_data(request_payload),
            response_status_code=200 if status != "Failed" else None,
            response_headers={},
            response_payload=mask_sensitive_data(response_payload),
            error_code=error_code,
            error_message=error_message,
            error_details=mask_sensitive_data(error_details or {}),
            duration_ms=duration_ms,
        )

    def create_outbound_http_log(self, **kwargs):
        return self.create_started_log(direction="Outbound", integration_system="1C", **kwargs)

    def get_logs(
        self,
        *,
        current_user_id: UUID,
        direction: str | None,
        operation_type: str | None,
        status: str | None,
        document_id: UUID | None,
        date_from,
        date_to,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> IntegrationLogsResponse:
        self._require_permission(current_user_id, "integration.log.read")
        rows, total = self.repository.list_logs(
            direction=direction,
            operation_type=operation_type,
            status=status,
            document_id=document_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = [self._to_list_item(log, document_number, initiated_by_name) for log, document_number, initiated_by_name in rows]
        return IntegrationLogsResponse(items=items, total=total, limit=limit, offset=offset)

    def get_log_by_id(self, log_id: UUID, current_user_id: UUID) -> IntegrationLogDetail:
        self._require_permission(current_user_id, "integration.log.read")
        row = self.repository.get_with_relations(log_id)
        if row is None:
            raise AppError("Integration log not found", code="INTEGRATION_LOG_NOT_FOUND", status_code=404)
        log, document_number, initiated_by_name = row
        item = self._to_list_item(log, document_number, initiated_by_name)
        return IntegrationLogDetail(
            **item.model_dump(),
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            request_url=log.request_url,
            request_method=log.request_method,
            request_headers=deepcopy(log.request_headers or {}),
            request_payload=deepcopy(log.request_payload or {}),
            response_headers=deepcopy(log.response_headers or {}),
            response_payload=deepcopy(log.response_payload or {}),
            error_details=deepcopy(log.error_details or {}),
            updated_at=log.updated_at,
        )

    def ensure_retry_supported(self, log_id: UUID):
        log = self._require_log(log_id)
        if log.direction != "Outbound" or log.operation_type != "1c_export_payment_request" or log.document_id is None:
            raise AppError(
                "Retry is supported only for outbound PaymentRequest export logs",
                code="INTEGRATION_LOG_RETRY_NOT_SUPPORTED",
                status_code=400,
            )
        return log

    def _require_log(self, log_id: UUID):
        log = self.repository.get_by_id(log_id)
        if log is None:
            raise AppError("Integration log not found", code="INTEGRATION_LOG_NOT_FOUND", status_code=404)
        return log

    def _to_list_item(self, log, document_number: str | None, initiated_by_name: str | None) -> IntegrationLogListItem:
        return IntegrationLogListItem(
            id=log.id,
            direction=log.direction,
            integration_system=log.integration_system,
            operation_type=log.operation_type,
            status=log.status,
            document_id=log.document_id,
            document_number=document_number,
            initiated_by=log.initiated_by,
            initiated_by_name=initiated_by_name,
            response_status_code=log.response_status_code,
            error_code=log.error_code,
            error_message=log.error_message,
            duration_ms=log.duration_ms,
            correlation_id=log.correlation_id,
            idempotency_key=log.idempotency_key,
            created_at=log.created_at,
        )

    def _require_permission(self, user_id: UUID, permission_code: str) -> None:
        permissions = get_user_permission_codes(self.repository.db, user_id)
        if "admin.access" in permissions or permission_code in permissions:
            return
        raise AppError(
            "Permission required",
            code="PERMISSION_DENIED",
            status_code=403,
            details={"permission": permission_code},
        )
