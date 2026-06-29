from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class OneCDiagnosticsSettings(BaseModel):
    one_c_enabled: bool
    base_url_configured: bool
    base_url_preview: str | None = None
    payment_request_endpoint: str
    health_endpoint: str
    timeout_seconds: int
    username_configured: bool
    password_configured: bool
    verify_ssl: bool


class OneCTestConnectionResult(BaseModel):
    status: Literal["ok", "disabled", "error", "warning"]
    one_c_enabled: bool
    base_url: str | None = None
    health_endpoint: str | None = None
    http_status: int | None = None
    duration_ms: int | None = None
    service: str | None = None
    version: str | None = None
    code: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None
