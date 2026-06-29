from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.modules.audit.models import AuditLog
from app.modules.integration.log_models import IntegrationOperationLog
from app.modules.payment_registers.models import PaymentRegister, PaymentRegisterRow
from app.modules.users.models import User
from tests.conftest import auth_headers
from tests.test_integration_1c_outbound import _create_approved_payment_request


def _accounting_admin_headers(db) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == "accounting_admin@example.com"))
    assert user is not None
    return auth_headers(str(user.id))


def _create_register(client, db, *, date: str = "2026-06-29") -> dict:
    response = client.post(
        "/api/v1/payment-registers",
        json={"date": date, "comment": "Autotest register"},
        headers=_accounting_admin_headers(db),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _latest_log(db, operation_type: str) -> IntegrationOperationLog:
    log = db.scalar(
        select(IntegrationOperationLog)
        .where(IntegrationOperationLog.operation_type == operation_type)
        .order_by(IntegrationOperationLog.created_at.desc())
    )
    assert log is not None
    return log


def test_payment_register_permissions_and_crud(client, db, users):
    no_auth = client.get("/api/v1/payment-registers")
    assert no_auth.status_code == 401

    no_permission = client.post(
        "/api/v1/payment-registers",
        json={"date": "2026-06-29"},
        headers=auth_headers(str(users["author"].id)),
    )
    assert no_permission.status_code == 403
    assert no_permission.json()["error"]["code"] == "PERMISSION_DENIED"

    created = _create_register(client, db)
    assert created["number"].startswith("REG-")
    register_id = created["id"]

    list_response = client.get("/api/v1/payment-registers", headers=_accounting_admin_headers(db))
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == register_id for item in list_response.json()["items"])

    update_response = client.put(
        f"/api/v1/payment-registers/{register_id}",
        json={"comment": "Updated comment"},
        headers=_accounting_admin_headers(db),
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["comment"] == "Updated comment"

    delete_response = client.delete(f"/api/v1/payment-registers/{register_id}", headers=_accounting_admin_headers(db))
    assert delete_response.status_code == 204
    assert db.get(PaymentRegister, register_id) is None


def test_available_payment_requests_excludes_success_exports_and_active_registers(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", False)
    doc_to_export = _create_approved_payment_request(client, db, users, seed_refs)
    export_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{doc_to_export['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert export_response.status_code == 200, export_response.text

    doc_in_active_register = _create_approved_payment_request(client, db, users, seed_refs)
    register = _create_register(client, db)
    add_response = client.post(
        f"/api/v1/payment-registers/{register['id']}/rows",
        json={"document_ids": [doc_in_active_register["id"]]},
        headers=_accounting_admin_headers(db),
    )
    assert add_response.status_code == 200, add_response.text

    available_response = client.get("/api/v1/payment-registers/available-payment-requests", headers=_accounting_admin_headers(db))
    assert available_response.status_code == 200, available_response.text
    available_ids = {item["document_id"] for item in available_response.json()["items"]}
    assert doc_to_export["id"] not in available_ids
    assert doc_in_active_register["id"] not in available_ids


def test_failed_exports_are_available_only_when_flag_is_enabled(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", True)
    document = _create_approved_payment_request(client, db, users, seed_refs)

    def one_c_error(self, payload):
        return {
            "status": "error",
            "error": {"code": "VALIDATION_ERROR", "message": "1C validation failed"},
            "one_c_enabled": True,
            "__meta__": {"response_status_code": 200, "response_headers": {}},
        }

    monkeypatch.setattr("app.modules.integration.one_c.outbound_client.OneCOutboundClient.send_payment_request", one_c_error)
    failed_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert failed_response.status_code == 200, failed_response.text
    assert failed_response.json()["status"] == "Failed"

    hidden_response = client.get("/api/v1/payment-registers/available-payment-requests", headers=_accounting_admin_headers(db))
    assert hidden_response.status_code == 200, hidden_response.text
    hidden_ids = {item["document_id"] for item in hidden_response.json()["items"]}
    assert document["id"] not in hidden_ids

    visible_response = client.get(
        "/api/v1/payment-registers/available-payment-requests",
        params={"include_failed_exports": True},
        headers=_accounting_admin_headers(db),
    )
    assert visible_response.status_code == 200, visible_response.text
    visible_ids = {item["document_id"] for item in visible_response.json()["items"]}
    assert document["id"] in visible_ids


def test_register_send_to_1c_updates_rows_and_logs(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", False)
    document = _create_approved_payment_request(client, db, users, seed_refs)
    register = _create_register(client, db)

    add_response = client.post(
        f"/api/v1/payment-registers/{register['id']}/rows",
        json={"document_ids": [document["id"]]},
        headers=_accounting_admin_headers(db),
    )
    assert add_response.status_code == 200, add_response.text
    assert add_response.json()["added_count"] == 1

    ready_response = client.post(
        f"/api/v1/payment-registers/{register['id']}/mark-ready",
        headers=_accounting_admin_headers(db),
    )
    assert ready_response.status_code == 200, ready_response.text
    assert ready_response.json()["payment_register"]["status"] == "ReadyToSend"

    send_response = client.post(
        f"/api/v1/payment-registers/{register['id']}/send-to-1c",
        headers=_accounting_admin_headers(db),
    )
    assert send_response.status_code == 200, send_response.text
    body = send_response.json()
    assert body["payment_register"]["status"] == "Sent"
    assert body["payment_register"]["sent_rows_count"] == 1
    assert body["results"][0]["export_status"] == "CreatedIn1C"

    row = db.scalar(select(PaymentRegisterRow).where(PaymentRegisterRow.register_id == register["id"]))
    assert row is not None
    assert row.export_status == "CreatedIn1C"
    assert row.one_c_payment_order_number == "FAKE-000001"

    log = _latest_log(db, "1c_export_payment_register")
    assert log.status == "Success"
    assert log.entity_type == "payment_register"

    final_audit = db.scalar(
        select(AuditLog)
        .where(AuditLog.entity_type == "payment_register", AuditLog.entity_id == register["id"], AuditLog.action == "payment_register_sent")
        .order_by(AuditLog.created_at.desc())
    )
    assert final_audit is not None
