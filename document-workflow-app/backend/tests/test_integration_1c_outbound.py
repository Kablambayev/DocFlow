from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.modules.audit.models import AuditLog
from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.documents.models import Document, DocumentApprovalStatus
from app.modules.integration.one_c.outbound_client import OneCOutboundClient
from app.modules.integration.one_c.payment_export_models import (
    PaymentRequest1CExport,
    PaymentRequest1CExportStatus,
)
from app.modules.notifications.models import Notification, NotificationType
from app.modules.users.models import User
from tests.conftest import auth_headers, create_test_document, pending_task_for_document


def _accounting_admin_headers(db) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == "accounting_admin@example.com"))
    assert user is not None
    return auth_headers(str(user.id))


def _accounting_admin(db) -> User:
    user = db.scalar(select(User).where(User.email == "accounting_admin@example.com"))
    assert user is not None
    return user


def _approve_document(client, db, document_id: str, approver_id: str) -> None:
    submit_response = client.post(f"/api/v1/documents/{document_id}/submit", headers=auth_headers(approver_id))
    assert submit_response.status_code == 200, submit_response.text
    db.expire_all()
    task = pending_task_for_document(db, document_id)
    approve_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/approve",
        json={"comment": "approved for 1C outbound"},
        headers=auth_headers(approver_id),
    )
    assert approve_response.status_code == 200, approve_response.text


def _create_approved_payment_request(client, db, users, seed_refs) -> dict:
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(
        f"/api/v1/documents/{document['id']}/submit",
        headers=auth_headers(str(users["author"].id)),
    )
    assert submit_response.status_code == 200, submit_response.text
    db.expire_all()
    task = pending_task_for_document(db, document["id"])
    approve_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/approve",
        json={"comment": "approved for 1C outbound"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert approve_response.status_code == 200, approve_response.text
    return document


def _get_export(db, document_id: str) -> PaymentRequest1CExport | None:
    return db.scalar(select(PaymentRequest1CExport).where(PaymentRequest1CExport.document_id == document_id))


def _create_non_payment_request_document(db, users) -> Document:
    document_type = DocumentType(
        code=f"TravelRequest-{uuid4().hex[:8]}",
        name="Travel Request",
        description="Test non-payment request",
        is_system=False,
        is_active=True,
    )
    db.add(document_type)
    db.flush()

    version = DocumentTypeVersion(
        document_type_id=document_type.id,
        version_number=1,
        status=VersionStatus.PUBLISHED,
        schema_json={"sections": [{"code": "main", "name": "Main", "fields": []}]},
        published_at=datetime.now(timezone.utc),
    )
    db.add(version)
    db.flush()

    document = Document(
        document_type_id=document_type.id,
        document_type_version_id=version.id,
        number=f"TR-{uuid4().hex[:6].upper()}",
        document_date=datetime.now(timezone.utc),
        author_id=users["author"].id,
        organization_id=None,
        department_id=None,
        approval_status=DocumentApprovalStatus.APPROVED,
        business_status=None,
        title="Travel test",
        data_json={},
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def test_send_requires_auth_and_permission(client, db, users, seed_refs):
    document = _create_approved_payment_request(client, db, users, seed_refs)

    no_auth = client.post(f"/api/v1/integration/1c/payment-requests/{document['id']}/send")
    assert no_auth.status_code == 401
    assert no_auth.json()["error"]["code"] == "AUTH_REQUIRED"

    no_permission = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=auth_headers(str(users["author"].id)),
    )
    assert no_permission.status_code == 403
    assert no_permission.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_and_accounting_admin_can_send(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", False)

    admin_document = _create_approved_payment_request(client, db, users, seed_refs)
    admin_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{admin_document['id']}/send",
        headers=auth_headers(str(users["admin"].id)),
    )
    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["status"] == PaymentRequest1CExportStatus.CREATED_IN_1C

    accounting_document = _create_approved_payment_request(client, db, users, seed_refs)
    accounting_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{accounting_document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert accounting_response.status_code == 200, accounting_response.text
    assert accounting_response.json()["status"] == PaymentRequest1CExportStatus.CREATED_IN_1C


def test_business_rules_for_status_and_document_type(client, db, users, seed_refs):
    draft_document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    draft_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{draft_document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert draft_response.status_code == 409
    assert draft_response.json()["error"]["code"] == "DOCUMENT_NOT_APPROVED"

    on_approval_document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(
        f"/api/v1/documents/{on_approval_document['id']}/submit",
        headers=auth_headers(str(users["author"].id)),
    )
    assert submit_response.status_code == 200, submit_response.text
    on_approval_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{on_approval_document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert on_approval_response.status_code == 409
    assert on_approval_response.json()["error"]["code"] == "DOCUMENT_NOT_APPROVED"

    approved_document = _create_approved_payment_request(client, db, users, seed_refs)
    approved_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{approved_document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert approved_response.status_code == 200, approved_response.text

    db_document = db.get(Document, approved_document["id"])
    assert db_document is not None
    db_document.approval_status = DocumentApprovalStatus.REJECTED
    db.commit()
    rejected_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{approved_document['id']}/send",
        headers=_accounting_admin_headers(db),
        params={"force": True},
    )
    assert rejected_response.status_code == 409
    assert rejected_response.json()["error"]["code"] == "DOCUMENT_NOT_APPROVED"

    non_payment_request = _create_non_payment_request_document(db, users)
    unsupported_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{non_payment_request.id}/send",
        headers=_accounting_admin_headers(db),
    )
    assert unsupported_response.status_code == 409
    assert unsupported_response.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT_TYPE"


def test_payload_mapping_contains_external_ids_and_hides_workflow_fields(client, db, users, seed_refs, monkeypatch):
    document = _create_approved_payment_request(client, db, users, seed_refs)
    monkeypatch.setattr(settings, "one_c_enabled", False)

    response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert response.status_code == 200, response.text

    export = _get_export(db, document["id"])
    assert export is not None
    payload = export.request_payload
    assert payload["organization_external_id"] == "ORG-001"
    assert payload["counterparty_external_id"] == "CNT-001"
    assert payload["contract_external_id"] == "CTR-ORG1-CNT1-142"
    assert payload["currency_external_id"] == "CUR-KZT"
    assert payload["expense_item_external_id"] == "EXP-002"
    assert payload["cash_flow_operation_type_code"] == "supplier_payment"
    assert payload["project_code"] == "MAIN"
    assert "approval_status" not in payload
    assert "workflow_state" not in payload
    assert "comments" not in payload
    assert "history" not in payload
    assert "files" not in payload


def test_fake_mode_creates_export_and_get_export_returns_payment_order(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", False)
    document = _create_approved_payment_request(client, db, users, seed_refs)

    send_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert send_response.status_code == 200, send_response.text
    body = send_response.json()
    assert body["status"] == PaymentRequest1CExportStatus.CREATED_IN_1C
    assert body["one_c_enabled"] is False
    assert body["payment_order"]["number"] == "FAKE-000001"

    export = _get_export(db, document["id"])
    assert export is not None
    assert export.status == PaymentRequest1CExportStatus.CREATED_IN_1C

    get_response = client.get(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/export",
        headers=auth_headers(str(users["author"].id)),
    )
    assert get_response.status_code == 200, get_response.text
    get_body = get_response.json()
    assert get_body["status"] == PaymentRequest1CExportStatus.CREATED_IN_1C
    assert get_body["one_c_payment_order_number"] == "FAKE-000001"


def test_repeated_send_without_force_returns_existing_export_and_force_resends(client, db, users, seed_refs, monkeypatch):
    document = _create_approved_payment_request(client, db, users, seed_refs)
    monkeypatch.setattr(settings, "one_c_enabled", True)
    call_counter = {"count": 0}

    def fake_send(self, payload):
        call_counter["count"] += 1
        return {
            "status": "created",
            "payment_order": {
                "external_id": f"po-{call_counter['count']}",
                "number": f"00000012{call_counter['count']}",
                "date": "2026-06-26",
                "amount": payload["amount"],
                "currency_code": "KZT",
            },
            "one_c_enabled": True,
        }

    monkeypatch.setattr("app.modules.integration.one_c.outbound_client.OneCOutboundClient.send_payment_request", fake_send)

    first = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert first.status_code == 200, first.text
    assert call_counter["count"] == 1

    second = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "already_exported"
    assert call_counter["count"] == 1

    third = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
        params={"force": True},
    )
    assert third.status_code == 200, third.text
    assert call_counter["count"] == 2

    export = _get_export(db, document["id"])
    assert export is not None
    assert export.one_c_payment_order_external_id == "po-2"


def test_mapping_error_returns_controlled_export_mapping_error(client, db, users, seed_refs):
    document = _create_approved_payment_request(client, db, users, seed_refs)
    db_document = db.get(Document, document["id"])
    assert db_document is not None
    data_json = deepcopy(db_document.data_json)
    data_json["organization_id"] = str(uuid4())
    db_document.data_json = data_json
    db.commit()

    response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "EXPORT_MAPPING_ERROR"
    assert error["details"]["field"] == "organization_id"


def test_1c_error_response_and_network_http_errors_store_failed_status(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", True)
    document = _create_approved_payment_request(client, db, users, seed_refs)
    original_send_payment_request = OneCOutboundClient.send_payment_request

    def one_c_error(self, payload):
        return {
            "status": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Не найден договор контрагента",
                "details": {"contract_external_id": payload["contract_external_id"]},
            },
            "one_c_enabled": True,
        }

    monkeypatch.setattr("app.modules.integration.one_c.outbound_client.OneCOutboundClient.send_payment_request", one_c_error)
    error_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=_accounting_admin_headers(db),
    )
    assert error_response.status_code == 200, error_response.text
    export = _get_export(db, document["id"])
    assert export is not None
    assert export.status == PaymentRequest1CExportStatus.FAILED
    assert export.error_code == "VALIDATION_ERROR"

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
        params={"force": True},
    )
    assert network_response.status_code == 200, network_response.text
    network_export = _get_export(db, network_document["id"])
    assert network_export is not None
    assert network_export.status == PaymentRequest1CExportStatus.FAILED
    assert network_export.error_code == "ONE_C_CONNECTION_ERROR"

    http_document = _create_approved_payment_request(client, db, users, seed_refs)

    class FakeResponse:
        status_code = 500

        def raise_for_status(self):
            request = httpx.Request("POST", "http://1c.local/payment-requests")
            response = httpx.Response(500, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    monkeypatch.setattr(httpx, "post", lambda url, json, timeout, auth: FakeResponse())
    http_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{http_document['id']}/send",
        headers=_accounting_admin_headers(db),
        params={"force": True},
    )
    assert http_response.status_code == 200, http_response.text
    http_export = _get_export(db, http_document["id"])
    assert http_export is not None
    assert http_export.status == PaymentRequest1CExportStatus.FAILED
    assert http_export.error_code == "ONE_C_HTTP_ERROR"


def test_success_and_failure_create_audit_and_notifications(client, db, users, seed_refs, monkeypatch):
    monkeypatch.setattr(settings, "one_c_enabled", False)
    document = _create_approved_payment_request(client, db, users, seed_refs)
    accounting_admin = _accounting_admin(db)

    success_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{document['id']}/send",
        headers=auth_headers(str(accounting_admin.id)),
    )
    assert success_response.status_code == 200, success_response.text

    success_audit = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "integration_1c_payment_request_created",
            AuditLog.entity_id == document["id"],
        )
    )
    assert success_audit is not None

    success_notification = db.scalar(
        select(Notification).where(
            Notification.document_id == document["id"],
            Notification.type == NotificationType.INTEGRATION_1C_PAYMENT_ORDER_CREATED,
            Notification.recipient_id == users["author"].id,
        )
    )
    assert success_notification is not None

    timeline_response = client.get(
        f"/api/v1/documents/{document['id']}/timeline",
        headers=auth_headers(str(users["author"].id)),
    )
    assert timeline_response.status_code == 200, timeline_response.text
    assert any(item["type"] == "integration_1c_payment_request_created" for item in timeline_response.json())

    failed_document = _create_approved_payment_request(client, db, users, seed_refs)

    def failed_send(self, payload):
        return {
            "status": "error",
            "error": {"code": "VALIDATION_ERROR", "message": "1C validation failed"},
            "one_c_enabled": False,
        }

    monkeypatch.setattr("app.modules.integration.one_c.outbound_client.OneCOutboundClient.send_payment_request", failed_send)
    monkeypatch.setattr(settings, "one_c_enabled", True)

    failed_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{failed_document['id']}/send",
        headers=auth_headers(str(accounting_admin.id)),
    )
    assert failed_response.status_code == 200, failed_response.text

    failed_audit = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "integration_1c_payment_request_failed",
            AuditLog.entity_id == failed_document["id"],
        )
    )
    assert failed_audit is not None

    failed_author_notification = db.scalar(
        select(Notification).where(
            Notification.document_id == failed_document["id"],
            Notification.type == NotificationType.INTEGRATION_1C_PAYMENT_REQUEST_FAILED,
            Notification.recipient_id == users["author"].id,
        )
    )
    assert failed_author_notification is not None

    failed_sender_notification = db.scalar(
        select(Notification).where(
            Notification.document_id == failed_document["id"],
            Notification.type == NotificationType.INTEGRATION_1C_PAYMENT_REQUEST_FAILED,
            Notification.recipient_id == accounting_admin.id,
        )
    )
    assert failed_sender_notification is not None