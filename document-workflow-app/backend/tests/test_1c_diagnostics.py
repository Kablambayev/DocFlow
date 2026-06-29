from __future__ import annotations

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.modules.integration.log_models import IntegrationOperationLog
from app.modules.integration.one_c.outbound_client import OneCOutboundClient
from tests.conftest import auth_headers


URL = "/api/v1/integration/1c/diagnostics"


def _latest_log(db):
    db.expire_all()
    item = db.scalar(
        select(IntegrationOperationLog)
        .where(IntegrationOperationLog.operation_type == "1c_test_connection")
        .order_by(IntegrationOperationLog.created_at.desc(), IntegrationOperationLog.id.desc())
    )
    assert item is not None
    return item


class FakeHttpClient:
    response = httpx.Response(200, json={"status": "ok"}, request=httpx.Request("GET", "http://1c/health"))
    error: Exception | None = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        if self.error:
            raise self.error
        return self.response


def test_diagnostics_permissions(client, users):
    assert client.get(f"{URL}/settings").status_code == 401
    assert client.get(f"{URL}/settings", headers=auth_headers(str(users["author"].id))).status_code == 403
    assert client.post(f"{URL}/test-connection", headers=auth_headers(str(users["author"].id))).status_code == 403
    assert client.get(f"{URL}/settings", headers=auth_headers(str(users["accounting_admin"].id))).status_code == 200
    assert client.post(f"{URL}/test-connection", headers=auth_headers(str(users["admin"].id))).status_code == 200


def test_settings_are_safe_and_flags_are_correct(client, users, monkeypatch):
    monkeypatch.setattr(settings, "one_c_base_url", "https://raw-user:raw-password@1c.example/base/hs/docflow")
    monkeypatch.setattr(settings, "one_c_username", "configured-user")
    monkeypatch.setattr(settings, "one_c_password", "configured-password")
    response = client.get(f"{URL}/settings", headers=auth_headers(str(users["accounting_admin"].id)))
    assert response.status_code == 200
    body = response.json()
    assert body["base_url_configured"] is True
    assert body["username_configured"] is True
    assert body["password_configured"] is True
    serialized = response.text
    assert "raw-user" not in serialized
    assert "raw-password" not in serialized
    assert "configured-user" not in serialized
    assert "configured-password" not in serialized


def test_disabled_and_missing_url_are_controlled_and_logged(client, db, users, monkeypatch):
    headers = auth_headers(str(users["accounting_admin"].id))
    monkeypatch.setattr(settings, "one_c_enabled", False)
    disabled = client.post(f"{URL}/test-connection", headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
    assert _latest_log(db).status == "Skipped"

    monkeypatch.setattr(settings, "one_c_enabled", True)
    monkeypatch.setattr(settings, "one_c_base_url", "")
    missing = client.post(f"{URL}/test-connection", headers=headers)
    assert missing.status_code == 200
    assert missing.json()["code"] == "ONE_C_BASE_URL_NOT_CONFIGURED"
    assert _latest_log(db).status == "Failed"


def test_health_success_warning_auth_and_http_errors(client, db, users, monkeypatch):
    headers = auth_headers(str(users["accounting_admin"].id))
    monkeypatch.setattr(settings, "one_c_enabled", True)
    monkeypatch.setattr(settings, "one_c_base_url", "http://1c.example")
    monkeypatch.setattr(httpx, "Client", FakeHttpClient)

    FakeHttpClient.error = None
    FakeHttpClient.response = httpx.Response(200, json={"status": "ok", "service": "1C", "version": "1.0"}, request=httpx.Request("GET", "http://1c.example/health"))
    success = client.post(f"{URL}/test-connection", headers=headers)
    assert success.json()["status"] == "ok"
    assert success.json()["service"] == "1C"
    assert _latest_log(db).status == "Success"

    FakeHttpClient.response = httpx.Response(200, text="OK", request=httpx.Request("GET", "http://1c.example/health"))
    warning = client.post(f"{URL}/test-connection", headers=headers)
    assert warning.json()["code"] == "ONE_C_HEALTH_NON_JSON_RESPONSE"
    assert _latest_log(db).status == "Success"

    for status_code, code in ((401, "ONE_C_AUTH_ERROR"), (500, "ONE_C_HTTP_ERROR")):
        FakeHttpClient.response = httpx.Response(status_code, json={"status": "error"}, request=httpx.Request("GET", "http://1c.example/health"))
        response = client.post(f"{URL}/test-connection", headers=headers)
        assert response.json()["code"] == code
        assert _latest_log(db).status == "Failed"


def test_timeout_and_connection_errors_are_controlled(monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", True)
    monkeypatch.setattr(settings, "one_c_base_url", "http://1c.example")
    monkeypatch.setattr(httpx, "Client", FakeHttpClient)

    FakeHttpClient.error = httpx.ReadTimeout("slow")
    assert OneCOutboundClient().test_connection()["code"] == "ONE_C_TIMEOUT"
    FakeHttpClient.error = httpx.ConnectError("down")
    assert OneCOutboundClient().test_connection()["code"] == "ONE_C_CONNECTION_ERROR"
    FakeHttpClient.error = None
