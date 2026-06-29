from __future__ import annotations

import logging
from time import perf_counter
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OneCOutboundClient:
    """HTTP client for DocFlow -> 1C export flow."""

    def __init__(self):
        self.base_url = settings.one_c_base_url
        self.username = settings.one_c_username
        self.password = settings.one_c_password
        self.timeout_seconds = settings.one_c_timeout_seconds
        self.enabled = settings.one_c_enabled
        self.payment_request_endpoint = settings.one_c_payment_request_endpoint
        self.health_endpoint = settings.one_c_health_endpoint
        self.connection_test_endpoint = settings.one_c_connection_test_endpoint
        self.verify_ssl = settings.one_c_verify_ssl

    @staticmethod
    def _safe_url(url: str) -> str:
        try:
            parts = urlsplit(url)
            hostname = parts.hostname or ""
            if parts.port:
                hostname = f"{hostname}:{parts.port}"
            query = urlencode([
                (key, "***MASKED***" if any(secret in key.lower() for secret in ("password", "token", "secret", "key")) else value)
                for key, value in parse_qsl(parts.query, keep_blank_values=True)
            ])
            return urlunsplit((parts.scheme, hostname, parts.path, query, ""))
        except ValueError:
            return ""

    def _health_url(self) -> str:
        endpoint = self.connection_test_endpoint or self.health_endpoint
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def check_health(self, endpoint: str | None = None) -> dict[str, Any]:
        selected_endpoint = endpoint or self.health_endpoint
        url = f"{self.base_url.rstrip('/')}/{selected_endpoint.lstrip('/')}"
        auth = (self.username, self.password) if self.username or self.password else None
        with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_ssl, auth=auth) as client:
            response = client.get(url)
        if response.status_code in {401, 403}:
            return {
                "status": "error", "code": "ONE_C_AUTH_ERROR",
                "message": "1C service returned authentication error", "http_status": response.status_code,
            }
        if response.status_code >= 400:
            return {
                "status": "error", "code": "ONE_C_HTTP_ERROR",
                "message": "1C service returned HTTP error", "http_status": response.status_code,
            }
        try:
            body = response.json()
        except ValueError:
            return {
                "status": "warning", "code": "ONE_C_HEALTH_NON_JSON_RESPONSE",
                "message": "1C health endpoint returned non-JSON response", "http_status": response.status_code,
            }
        result: dict[str, Any] = {"status": "ok", "http_status": response.status_code}
        if isinstance(body, dict):
            result.update({key: body[key] for key in ("service", "version") if body.get(key) is not None})
        return result

    def test_connection(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                "status": "disabled", "one_c_enabled": False,
                "message": "1C integration is disabled. Real HTTP calls are not performed.",
            }
        if not self.base_url.strip():
            return {
                "status": "error", "one_c_enabled": True, "code": "ONE_C_BASE_URL_NOT_CONFIGURED",
                "message": "ONE_C_BASE_URL is not configured",
            }
        started_at = perf_counter()
        common = {
            "one_c_enabled": True,
            "base_url": self._safe_url(self.base_url),
            "health_endpoint": self.connection_test_endpoint or self.health_endpoint,
        }
        try:
            result = self.check_health(self.connection_test_endpoint or self.health_endpoint)
        except httpx.TimeoutException:
            result = {
                "status": "error", "code": "ONE_C_TIMEOUT",
                "message": "1C service did not respond within timeout",
                "details": {"timeout_seconds": self.timeout_seconds},
            }
        except httpx.HTTPError:
            result = {
                "status": "error", "code": "ONE_C_CONNECTION_ERROR",
                "message": "Cannot connect to 1C service",
            }
        result.update(common)
        result["duration_ms"] = int((perf_counter() - started_at) * 1000)
        return result

    def send_payment_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{self.payment_request_endpoint}"
        auth = None
        request_headers: dict[str, Any] = {}
        if self.username or self.password:
            auth = (self.username, self.password)
            request_headers["Authorization"] = "***MASKED***"
        if not self.base_url.strip():
            return {
                "status": "error",
                "error": {
                    "code": "ONE_C_CONNECTION_ERROR",
                    "message": "Cannot connect to 1C service",
                },
                "one_c_enabled": self.enabled,
                "__meta__": {
                    "request_url": url,
                    "request_method": "POST",
                    "request_headers": request_headers,
                    "response_status_code": None,
                    "response_headers": {},
                },
            }
        try:
            request_kwargs = {"json": payload, "timeout": self.timeout_seconds, "auth": auth}
            if not self.verify_ssl:
                request_kwargs["verify"] = False
            response = httpx.post(url, **request_kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.exception("1C service returned HTTP error")
            return {
                "status": "error",
                "error": {
                    "code": "ONE_C_HTTP_ERROR",
                    "message": "1C service returned HTTP error",
                    "details": {"status_code": exc.response.status_code},
                },
                "one_c_enabled": self.enabled,
                "__meta__": {
                    "request_url": url,
                    "request_method": "POST",
                    "request_headers": request_headers,
                    "response_status_code": exc.response.status_code,
                    "response_headers": dict(exc.response.headers),
                },
            }
        except httpx.HTTPError:
            logger.exception("Cannot connect to 1C service")
            return {
                "status": "error",
                "error": {
                    "code": "ONE_C_CONNECTION_ERROR",
                    "message": "Cannot connect to 1C service",
                },
                "one_c_enabled": self.enabled,
                "__meta__": {
                    "request_url": url,
                    "request_method": "POST",
                    "request_headers": request_headers,
                    "response_status_code": None,
                    "response_headers": {},
                },
            }
        try:
            body = response.json()
        except ValueError:
            logger.exception("1C service returned non-JSON response")
            return {
                "status": "error",
                "error": {
                    "code": "ONE_C_HTTP_ERROR",
                    "message": "1C service returned HTTP error",
                    "details": {"status_code": response.status_code},
                },
                "one_c_enabled": self.enabled,
                "__meta__": {
                    "request_url": url,
                    "request_method": "POST",
                    "request_headers": request_headers,
                    "response_status_code": response.status_code,
                    "response_headers": dict(response.headers),
                },
            }
        body["one_c_enabled"] = self.enabled
        body["__meta__"] = {
            "request_url": url,
            "request_method": "POST",
            "request_headers": request_headers,
            "response_status_code": response.status_code,
            "response_headers": dict(response.headers),
        }
        return body
