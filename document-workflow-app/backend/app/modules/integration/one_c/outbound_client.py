from __future__ import annotations

import logging
from typing import Any

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
            response = httpx.post(url, json=payload, timeout=self.timeout_seconds, auth=auth)
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
