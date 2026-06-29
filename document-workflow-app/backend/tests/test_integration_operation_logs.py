from __future__ import annotations

from uuid import uuid4

import httpx
from sqlalchemy import func, select

from app.core.config import settings
from app.modules.integration.log_models import IntegrationOperationLog
from app.modules.integration.one_c.outbound_client import OneCOutboundClient
from app.modules.users.models import User
from tests.conftest import auth_headers
from tests.test_integration_1c_outbound import _accounting_admin_headers, _create_approved_payment_request


def _accounting_admin(db) -> User:
    user = db.scalar(select(User).where(User.email == "accounting_admin@example.com"))
    assert user is not None
    return user


def _latest_log(db, operation_type: str) -> IntegrationOperationLog:
    log = db.scalar(
        select(IntegrationOperationLog)
        .where(IntegrationOperationLog.operation_type == operation_type)
        .order_by(IntegrationOperationLog.created_at.desc())
    )
    assert log is not None
    return log


def test_logs_permissions(client, db, users):
    no_auth = client.get("/api/v1/integration/logs")
    assert no_auth.status_code == 401
    assert no_auth.json()["error"]["code"] == "AUTH_REQUIRED"

    no_permission = client.get("/api/v1/integration/logs", headers=auth_headers(str(users["author"].id)))
    assert no_permission.status_code == 403
    assert no_permission.json()["error"]["code"] == "PERMISSION_DENIED"

    accounting_admin = client.get("/api/v1/integration/logs", headers=_accounting_admin_headers(db))
    assert accounting_admin.status_code == 200, accounting_admin.text

    admin = client.get("/api/v1/integration/logs", headers=auth_headers(str(users["admin"].id)))
    assert admin.status_code == 200, admin.text


def test_inbound_logs_created_filtered_and_masked(client, db, users):
    payload = {
        "source_system": "1C",
        "items": [
            {
                "external_id": f"ORG-LOG-{uuid4().hex[:8]}",
                "code": f"ORG-LOG-{uuid4().hex[:4]}",
                "name": "Integration Log Org",
                "raw_data": {"token": "super-secret-token", "nested": {"password": "12345"}},
            }
        ],
    }
    response = client.post(
        "/api/v1/integration/1c/organizations/import",
        json=payload,
        headers=_accounting_admin_headers(db),
    )
    assert response.status_code == 200, response.text

    log = _latest_log(db, "1c_import_organizations")
    assert log.direction == "Inbound"
    assert log.status == "Success"
    assert log.request_payload["items"][0]["raw_data"]["token"] == "***MASKED***"
    assert log.request_payload["items"][0]["raw_data"]["nested"]["password"] == "***MASKED***"

    filtered = client.get(
        "/api/v1/integration/logs",
        params={"direction": "Inbound", "operation_type": "1c_import_organizations"},
        headers=_accounting_admin_headers(db),
    )
    assert filtered.status_code == 200, filtered.text
    body = filtered.json()
    assert body["total"] >= 1
    assert any(item["operation_type"] == "1c_import_organizations" for item in body["items"])


def test_inbound_partial_success_creates_partialsuccess_log(client, db):
    payload = {
        "source_system": "1C",
        "items": [
            {
                "external_id": f"ORG-PARTIAL-{uuid4().hex[:8]}",
                "code": f"ORG-PARTIAL-{uuid4().hex[:4]}",
                "name": "Partial Org",
            },
            {
                "external_id": f"ORG-PARTIAL-BAD-{uuid4().hex[:8]}",
                "name": "Bad Org Without Code But Valid Enough",
                "raw_data": {"api_key": "hidden"},
            },
        ],
    }
    response = client.post(
        "/api/v1/integration/1c/currencies/import",
        json=payload,
        headers=_accounting_admin_headers(db),
    )
    assert response.status_code == 200, response.text
    assert response.json()["skipped"] >= 1

    log = _latest_log(db, "1c_import_currencies")
    assert log.status == "PartialSuccess"


def test_outbound_log_created_fake_mode_and_detail_masks_headers(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", False)
    monkeypatch.setattr(settings, "one_c_username", "docflow")
    monkeypatch.setattr(settings, "one_c_password", "super-secret")

    document = _create_approved_payment_request(client, db, users, seed_refs)
    response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert response.status_code == 200, response.text

    log = _latest_log(db, "1c_export_payment_request")
    assert log.direction == "Outbound"
    assert log.status == "Success"
    assert str(log.document_id) == document["id"]
    assert log.idempotency_key == document["id"]
    assert log.request_url == "fake://1c/payment-requests"
    assert log.response_payload["fake_mode"] is True
    assert log.response_payload["one_c_enabled"] is False

    detail = client.get(f"/api/v1/integration/logs/{log.id}", headers=_accounting_admin_headers(db))
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["request_headers"]["Authorization"] == "***MASKED***"
    assert detail_body["request_payload"]["request_id"] == document["id"]


def test_outbound_failed_logs_for_1c_error_and_transport_errors(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", True)
    document = _create_approved_payment_request(client, db, users, seed_refs)
    original_send_payment_request = OneCOutboundClient.send_payment_request

    def one_c_error(self, payload):
        return {
            "status": "error",
            "error": {"code": "VALIDATION_ERROR", "message": "1C validation failed"},
            "one_c_enabled": True,
            "__meta__": {
                "request_url": "http://1c.local/payment-requests",
                "request_method": "POST",
                "request_headers": {"Authorization": "***MASKED***"},
                "response_status_code": 200,
                "response_headers": {},
            },
        }

    monkeypatch.setattr("app.modules.integration.one_c.outbound_client.OneCOutboundClient.send_payment_request", one_c_error)
    error_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert error_response.status_code == 200, error_response.text
    failed_log = _latest_log(db, "1c_export_payment_request")
    assert failed_log.status == "Failed"
    assert failed_log.error_code == "VALIDATION_ERROR"

    monkeypatch.setattr(
        "app.modules.integration.one_c.outbound_client.OneCOutboundClient.send_payment_request",
        original_send_payment_request,
    )

    network_document = _create_approved_payment_request(client, db, users, seed_refs)

    def raise_connect_error(url, json, timeout, auth):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", raise_connect_error)
    network_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{network_document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert network_response.status_code == 200, network_response.text
    network_log = _latest_log(db, "1c_export_payment_request")
    assert network_log.status == "Failed"
    assert network_log.error_code == "ONE_C_CONNECTION_ERROR"


def test_retry_supported_only_for_outbound_payment_request_export(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", False)
    document = _create_approved_payment_request(client, db, users, seed_refs)
    send_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert send_response.status_code == 200, send_response.text

    export_log = _latest_log(db, "1c_export_payment_request")
    before_retry_count = db.scalar(
        select(func.count(IntegrationOperationLog.id)).where(
            IntegrationOperationLog.operation_type == "1c_export_payment_request",
            IntegrationOperationLog.document_id == document["id"],
        )
    )

    retry_response = client.post(
        f"/api/v1/integration/logs/{export_log.id}/retry",
        headers=_accounting_admin_headers(db),
    )
    assert retry_response.status_code == 200, retry_response.text
    after_retry_count = db.scalar(
        select(func.count(IntegrationOperationLog.id)).where(
            IntegrationOperationLog.operation_type == "1c_export_payment_request",
            IntegrationOperationLog.document_id == document["id"],
        )
    )
    assert after_retry_count == before_retry_count + 1

    inbound_payload = {
        "source_system": "1C",
        "items": [{"external_id": f"ORG-RETRY-{uuid4().hex[:8]}", "code": "ORG-RETRY", "name": "Retry Org"}],
    }
    inbound_response = client.post(
        "/api/v1/integration/1c/organizations/import",
        json=inbound_payload,
        headers=_accounting_admin_headers(db),
    )
    assert inbound_response.status_code == 200, inbound_response.text
    inbound_log = _latest_log(db, "1c_import_organizations")

    unsupported_retry = client.post(
        f"/api/v1/integration/logs/{inbound_log.id}/retry",
        headers=_accounting_admin_headers(db),
    )
    assert unsupported_retry.status_code == 400
    assert unsupported_retry.json()["error"]["code"] == "INTEGRATION_LOG_RETRY_NOT_SUPPORTED"

    denied_retry = client.post(
        f"/api/v1/integration/logs/{export_log.id}/retry",
        headers=auth_headers(str(users["author"].id)),
    )
    assert denied_retry.status_code == 403
    assert denied_retry.json()["error"]["code"] == "PERMISSION_DENIED"
