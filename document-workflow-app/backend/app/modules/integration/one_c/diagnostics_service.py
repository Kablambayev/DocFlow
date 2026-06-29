from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.config import settings
from app.modules.integration.log_repository import IntegrationLogRepository
from app.modules.integration.log_service import IntegrationLogService
from app.modules.integration.one_c.outbound_client import OneCOutboundClient


def safe_url_preview(value: str) -> str | None:
    if not value.strip():
        return None
    try:
        parts = urlsplit(value)
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        query = urlencode([
            (key, "***MASKED***" if any(secret in key.lower() for secret in ("password", "token", "secret", "key")) else item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
        ])
        return urlunsplit((parts.scheme, host, parts.path, query, ""))
    except ValueError:
        return None


class OneCDiagnosticsService:
    def __init__(self, repository: IntegrationLogRepository, client: OneCOutboundClient):
        self.repository = repository
        self.client = client
        self.log_service = IntegrationLogService(repository)

    def get_settings(self) -> dict:
        return {
            "one_c_enabled": settings.one_c_enabled,
            "base_url_configured": bool(settings.one_c_base_url.strip()),
            "base_url_preview": safe_url_preview(settings.one_c_base_url),
            "payment_request_endpoint": settings.one_c_payment_request_endpoint,
            "health_endpoint": settings.one_c_health_endpoint,
            "timeout_seconds": settings.one_c_timeout_seconds,
            "username_configured": bool(settings.one_c_username),
            "password_configured": bool(settings.one_c_password),
            "verify_ssl": settings.one_c_verify_ssl,
        }

    def test_connection(self, initiated_by) -> dict:
        result = self.client.test_connection()
        duration_ms = result.get("duration_ms")
        http_status = result.get("http_status")
        request_url = (
            f"{self.client.base_url.rstrip('/')}/{(self.client.connection_test_endpoint or self.client.health_endpoint).lstrip('/')}"
            if self.client.enabled and self.client.base_url.strip()
            else "disabled://1c/health" if not self.client.enabled else "unconfigured://1c/health"
        )
        log = self.log_service.create_outbound_http_log(
            operation_type="1c_test_connection",
            status="Started",
            initiated_by=initiated_by,
            request_url=safe_url_preview(request_url),
            request_method="GET",
        )
        if result["status"] == "disabled":
            self.log_service.mark_success(log.id, response_payload=result, duration_ms=duration_ms, status="Skipped")
        elif result["status"] in {"ok", "warning"}:
            self.log_service.mark_success(
                log.id, response_status_code=http_status, response_payload=result, duration_ms=duration_ms
            )
        else:
            self.log_service.mark_failed(
                log.id, response_status_code=http_status, response_payload=result,
                error_code=result.get("code"), error_message=result.get("message"),
                error_details=result.get("details") or {}, duration_ms=duration_ms,
            )
        self.repository.db.commit()
        return result
