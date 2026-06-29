from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.documents.models import Document, DocumentApprovalStatus
from app.modules.integration.one_c.payment_export_models import PaymentRequest1CExport, PaymentRequest1CExportStatus
from tests.conftest import auth_headers, create_test_document, pending_task_for_document


def _accounting_admin_headers(users) -> dict[str, str]:
    return auth_headers(str(users["accounting_admin"].id))


def _approve_document(client, db, document_id: str, author_id: str, approver_id: str) -> None:
    submit_response = client.post(f"/api/v1/documents/{document_id}/submit", headers=auth_headers(author_id))
    assert submit_response.status_code == 200, submit_response.text
    db.expire_all()
    task = pending_task_for_document(db, document_id)
    approve_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/approve",
        json={"comment": "approved for treasury"},
        headers=auth_headers(approver_id),
    )
    assert approve_response.status_code == 200, approve_response.text


def _reject_document(client, db, document_id: str, author_id: str, approver_id: str) -> None:
    submit_response = client.post(f"/api/v1/documents/{document_id}/submit", headers=auth_headers(author_id))
    assert submit_response.status_code == 200, submit_response.text
    db.expire_all()
    task = pending_task_for_document(db, document_id)
    reject_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/reject",
        json={"comment": "rejected for treasury"},
        headers=auth_headers(approver_id),
    )
    assert reject_response.status_code == 200, reject_response.text


def _create_approved_payment_request(client, db, users, seed_refs, *, title: str | None = None, number: str | None = None) -> dict:
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    if title or number:
        db_document = db.get(Document, document["id"])
        assert db_document is not None
        if title:
            db_document.title = title
        if number:
            db_document.number = number
        db.commit()
    _approve_document(client, db, document["id"], str(users["author"].id), str(users["approver"].id))
    return document


def _create_non_payment_request_document(db, users, *, approval_status: str = DocumentApprovalStatus.APPROVED) -> Document:
    document_type = DocumentType(
        code=f"TravelRequest-{uuid4().hex[:8]}",
        name="Travel Request",
        description="Treasury test non-payment request",
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
        approval_status=approval_status,
        business_status=None,
        title="Travel treasury test",
        data_json={},
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def _set_export(db, document_id: str, *, status: str, amount: Decimal = Decimal("1000.00"), error_code: str | None = None) -> None:
    existing = db.scalar(select(PaymentRequest1CExport).where(PaymentRequest1CExport.document_id == document_id))
    if existing is None:
        existing = PaymentRequest1CExport(
            document_id=document_id,
            status=status,
            sent_at=datetime.now(timezone.utc),
            sent_by=None,
            request_payload={"request_id": document_id},
            response_payload={"status": status},
            one_c_payment_order_external_id=f"po-{document_id}" if status in [PaymentRequest1CExportStatus.CREATED_IN_1C, PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C] else None,
            one_c_payment_order_number="000000123" if status in [PaymentRequest1CExportStatus.CREATED_IN_1C, PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C] else None,
            one_c_payment_order_date=datetime.now(timezone.utc).date() if status in [PaymentRequest1CExportStatus.CREATED_IN_1C, PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C] else None,
            one_c_payment_order_amount=amount if status in [PaymentRequest1CExportStatus.CREATED_IN_1C, PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C] else None,
            one_c_payment_order_currency_code="KZT" if status in [PaymentRequest1CExportStatus.CREATED_IN_1C, PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C] else None,
            error_code=error_code,
            error_message="1C error" if error_code else None,
        )
        db.add(existing)
    else:
        existing.status = status
        existing.error_code = error_code
        existing.error_message = "1C error" if error_code else None
    db.commit()


def test_treasury_registry_permissions(client, users):
    no_auth = client.get("/api/v1/treasury/payment-requests")
    assert no_auth.status_code == 401
    assert no_auth.json()["error"]["code"] == "AUTH_REQUIRED"

    no_permission = client.get("/api/v1/treasury/payment-requests", headers=auth_headers(str(users["author"].id)))
    assert no_permission.status_code == 403
    assert no_permission.json()["error"]["code"] == "PERMISSION_DENIED"

    admin = client.get("/api/v1/treasury/payment-requests", headers=auth_headers(str(users["admin"].id)))
    assert admin.status_code == 200, admin.text

    accounting_admin = client.get("/api/v1/treasury/payment-requests", headers=_accounting_admin_headers(users))
    assert accounting_admin.status_code == 200, accounting_admin.text


def test_registry_returns_only_approved_payment_requests_and_export_statuses(client, db, users, seed_refs):
    not_exported = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-TREASURY-001")
    created = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-TREASURY-002")
    failed = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-TREASURY-003")

    draft = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    on_approval = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    _ = client.post(f"/api/v1/documents/{on_approval['id']}/submit", headers=auth_headers(str(users["author"].id)))
    rejected = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    _reject_document(client, db, rejected["id"], str(users["author"].id), str(users["approver"].id))
    other_type = _create_non_payment_request_document(db, users)

    _set_export(db, created["id"], status=PaymentRequest1CExportStatus.CREATED_IN_1C, amount=Decimal("2000.00"))
    _set_export(db, failed["id"], status=PaymentRequest1CExportStatus.FAILED, error_code="ONE_C_CONNECTION_ERROR")

    response = client.get("/api/v1/treasury/payment-requests", headers=_accounting_admin_headers(users))
    assert response.status_code == 200, response.text
    body = response.json()
    ids = {item["document_id"]: item for item in body["items"]}

    assert not_exported["id"] in ids
    assert created["id"] in ids
    assert failed["id"] in ids
    assert draft["id"] not in ids
    assert on_approval["id"] not in ids
    assert rejected["id"] not in ids
    assert str(other_type.id) not in ids
    assert ids[not_exported["id"]]["export"] is None
    assert ids[created["id"]]["export"]["status"] == PaymentRequest1CExportStatus.CREATED_IN_1C
    assert ids[failed["id"]]["export"]["status"] == PaymentRequest1CExportStatus.FAILED


def test_registry_filters_by_export_status_and_search(client, db, users, seed_refs):
    not_exported = _create_approved_payment_request(client, db, users, seed_refs, title="Treasury Alpha", number="PAY-SEARCH-001")
    created = _create_approved_payment_request(client, db, users, seed_refs, title="Treasury Beta", number="PAY-SEARCH-002")
    failed = _create_approved_payment_request(client, db, users, seed_refs, title="Gamma Error", number="PAY-SEARCH-003")
    _set_export(db, created["id"], status=PaymentRequest1CExportStatus.CREATED_IN_1C, amount=Decimal("2500.00"))
    _set_export(db, failed["id"], status=PaymentRequest1CExportStatus.FAILED, error_code="ONE_C_HTTP_ERROR")

    not_exported_response = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"export_status": "not_exported"},
    )
    assert not_exported_response.status_code == 200, not_exported_response.text
    not_exported_items = not_exported_response.json()["items"]
    assert not_exported["id"] in {item["document_id"] for item in not_exported_items}
    assert all(item["export"] is None for item in not_exported_items)

    created_response = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"export_status": PaymentRequest1CExportStatus.CREATED_IN_1C},
    )
    assert created_response.status_code == 200, created_response.text
    created_items = created_response.json()["items"]
    assert created["id"] in {item["document_id"] for item in created_items}
    assert all(item["export"]["status"] == PaymentRequest1CExportStatus.CREATED_IN_1C for item in created_items)

    failed_response = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"export_status": PaymentRequest1CExportStatus.FAILED},
    )
    assert failed_response.status_code == 200, failed_response.text
    failed_items = failed_response.json()["items"]
    assert failed["id"] in {item["document_id"] for item in failed_items}
    assert all(item["export"]["status"] == PaymentRequest1CExportStatus.FAILED for item in failed_items)

    search_number = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"search": "PAY-SEARCH-002"},
    )
    assert search_number.status_code == 200, search_number.text
    search_number_items = search_number.json()["items"]
    assert created["id"] in {item["document_id"] for item in search_number_items}
    assert all("pay-search-002" in item["number"].lower() or "pay-search-002" in (item["title"] or "").lower() for item in search_number_items)

    search_title = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"search": "Gamma"},
    )
    assert search_title.status_code == 200, search_title.text
    search_title_items = search_title.json()["items"]
    assert failed["id"] in {item["document_id"] for item in search_title_items}
    assert all("gamma" in item["number"].lower() or "gamma" in (item["title"] or "").lower() for item in search_title_items)


def test_registry_filters_by_dictionary_and_amount_and_pagination(client, db, users, seed_refs):
    first = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-FILTER-001")
    second = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-FILTER-002")
    third = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-FILTER-003")

    for document_id, amount in [(first["id"], 1000), (second["id"], 2500), (third["id"], 5000)]:
        db_document = db.get(Document, document_id)
        assert db_document is not None
        db_document.data_json = {**db_document.data_json, "amount": amount}
    db.commit()

    organization_id = seed_refs["accounting_data"]["organization_id"]
    counterparty_id = seed_refs["accounting_data"]["counterparty_id"]
    project_id = seed_refs["accounting_data"]["project_id"]

    by_organization = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"organization_id": organization_id},
    )
    assert by_organization.status_code == 200, by_organization.text
    assert len(by_organization.json()["items"]) >= 3

    by_counterparty = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"counterparty_id": counterparty_id},
    )
    assert by_counterparty.status_code == 200, by_counterparty.text
    assert len(by_counterparty.json()["items"]) >= 3

    by_project = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"project_id": project_id},
    )
    assert by_project.status_code == 200, by_project.text
    assert len(by_project.json()["items"]) >= 3

    by_amount = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"amount_from": "2000", "amount_to": "4000", "sort_by": "amount", "sort_order": "asc"},
    )
    assert by_amount.status_code == 200, by_amount.text
    amount_ids = {item["document_id"] for item in by_amount.json()["items"]}
    assert second["id"] in amount_ids
    assert first["id"] not in amount_ids
    assert third["id"] not in amount_ids

    paged = client.get(
        "/api/v1/treasury/payment-requests",
        headers=_accounting_admin_headers(users),
        params={"sort_by": "number", "sort_order": "asc", "limit": 1, "offset": 1},
    )
    assert paged.status_code == 200, paged.text
    page_body = paged.json()
    assert page_body["limit"] == 1
    assert page_body["offset"] == 1
    assert page_body["total"] >= 3
    assert len(page_body["items"]) == 1


def test_treasury_metrics_counts_and_sums(client, db, users, seed_refs):
    ready = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-METRIC-001")
    created = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-METRIC-002")
    already_exists = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-METRIC-003")
    failed = _create_approved_payment_request(client, db, users, seed_refs, number="PAY-METRIC-004")
    draft = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)

    for document_id, amount in [
        (ready["id"], 1500),
        (created["id"], 2200),
        (already_exists["id"], 3300),
        (failed["id"], 4400),
        (draft["id"], 5500),
    ]:
        db_document = db.get(Document, document_id)
        assert db_document is not None
        db_document.data_json = {**db_document.data_json, "amount": amount}
    db.commit()

    _set_export(db, created["id"], status=PaymentRequest1CExportStatus.CREATED_IN_1C, amount=Decimal("2200.00"))
    _set_export(db, already_exists["id"], status=PaymentRequest1CExportStatus.ALREADY_EXISTS_IN_1C, amount=Decimal("3300.00"))
    _set_export(db, failed["id"], status=PaymentRequest1CExportStatus.FAILED, error_code="ONE_C_HTTP_ERROR")

    response = client.get("/api/v1/treasury/payment-requests/metrics", headers=_accounting_admin_headers(users))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["ready_to_send"] >= 1
    assert body["created_in_1c"] >= 1
    assert body["already_exists_in_1c"] >= 1
    assert body["failed"] >= 1
    assert Decimal(str(body["total_amount_ready"])) >= Decimal("1500")
    assert Decimal(str(body["total_amount_created_in_1c"])) >= Decimal("2200")
