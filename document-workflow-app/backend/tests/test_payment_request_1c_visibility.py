from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.documents.models import Document, DocumentApprovalStatus
from tests.conftest import auth_headers, create_test_document, pending_task_for_document


def _create_approved_payment_request(
    client,
    db,
    users,
    seed_refs,
    *,
    actor_key: str = "author",
    author_key: str = "author",
) -> dict:
    document = create_test_document(client, str(users[actor_key].id), str(users[author_key].id), seed_refs)
    submit_response = client.post(
        f"/api/v1/documents/{document['id']}/submit",
        headers=auth_headers(str(users[actor_key].id)),
    )
    assert submit_response.status_code == 200, submit_response.text
    db.expire_all()
    task = pending_task_for_document(db, document["id"])
    approve_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/approve",
        json={"comment": "approved for visibility"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert approve_response.status_code == 200, approve_response.text
    return document


def _create_non_payment_request_document(db, users, *, approval_status: str = DocumentApprovalStatus.APPROVED) -> Document:
    document_type = DocumentType(
        code=f"TravelRequest-{uuid4().hex[:8]}",
        name="Travel Request",
        description="Visibility test non-payment request",
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
        title="Travel visibility test",
        data_json={},
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def test_accounting_admin_sees_only_approved_payment_requests_in_document_list(client, db, users, seed_refs):
    approved_payment_request = _create_approved_payment_request(client, db, users, seed_refs)
    draft_payment_request = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)

    on_approval_payment_request = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(
        f"/api/v1/documents/{on_approval_payment_request['id']}/submit",
        headers=auth_headers(str(users["author"].id)),
    )
    assert submit_response.status_code == 200, submit_response.text

    rejected_payment_request = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    reject_submit = client.post(
        f"/api/v1/documents/{rejected_payment_request['id']}/submit",
        headers=auth_headers(str(users["author"].id)),
    )
    assert reject_submit.status_code == 200, reject_submit.text
    db.expire_all()
    reject_task = pending_task_for_document(db, rejected_payment_request["id"])
    reject_response = client.post(
        f"/api/v1/workflow/tasks/{reject_task.id}/reject",
        json={"comment": "reject for visibility"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert reject_response.status_code == 200, reject_response.text

    approved_non_payment_request = _create_non_payment_request_document(db, users)

    response = client.get("/api/v1/documents", headers=auth_headers(str(users["accounting_admin"].id)))
    assert response.status_code == 200, response.text
    items = {item["id"]: item for item in response.json()}

    assert approved_payment_request["id"] in items
    assert draft_payment_request["id"] not in items
    assert on_approval_payment_request["id"] not in items
    assert rejected_payment_request["id"] not in items
    assert str(approved_non_payment_request.id) not in items


def test_accounting_admin_can_open_only_approved_payment_request_directly(client, db, users, seed_refs):
    approved_payment_request = _create_approved_payment_request(client, db, users, seed_refs)
    draft_payment_request = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    approved_non_payment_request = _create_non_payment_request_document(db, users)

    approved_response = client.get(
        f"/api/v1/documents/{approved_payment_request['id']}",
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert approved_response.status_code == 200, approved_response.text

    draft_response = client.get(
        f"/api/v1/documents/{draft_payment_request['id']}",
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert draft_response.status_code == 403
    assert draft_response.json()["error"]["code"] == "DOCUMENT_ACCESS_DENIED"

    other_type_response = client.get(
        f"/api/v1/documents/{approved_non_payment_request.id}",
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert other_type_response.status_code == 403
    assert other_type_response.json()["error"]["code"] == "DOCUMENT_ACCESS_DENIED"


def test_accounting_admin_can_send_and_read_export_for_approved_payment_request(client, db, users, seed_refs):
    approved_payment_request = _create_approved_payment_request(client, db, users, seed_refs)

    send_response = client.post(
        f"/api/v1/integration/1c/payment-requests/{approved_payment_request['id']}/send",
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert send_response.status_code == 200, send_response.text

    export_response = client.get(
        f"/api/v1/integration/1c/payment-requests/{approved_payment_request['id']}/export",
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert export_response.status_code == 200, export_response.text
    assert export_response.json()["status"] == "CreatedIn1C"


def test_document_user_without_export_permission_does_not_see_foreign_approved_payment_request(client, db, users, seed_refs):
    approved_payment_request = _create_approved_payment_request(client, db, users, seed_refs)

    list_response = client.get("/api/v1/documents", headers=auth_headers(str(users["approver"].id)))
    assert list_response.status_code == 200, list_response.text
    visible_ids = {item["id"] for item in list_response.json()}
    assert approved_payment_request["id"] in visible_ids

    foreign_document = _create_approved_payment_request(client, db, users, seed_refs, actor_key="admin", author_key="approver")
    user_list_response = client.get("/api/v1/documents", headers=auth_headers(str(users["author"].id)))
    assert user_list_response.status_code == 200, user_list_response.text
    user_visible_ids = {item["id"] for item in user_list_response.json()}
    assert foreign_document["id"] not in user_visible_ids

    direct_response = client.get(
        f"/api/v1/documents/{foreign_document['id']}",
        headers=auth_headers(str(users["author"].id)),
    )
    assert direct_response.status_code == 403
    assert direct_response.json()["error"]["code"] == "DOCUMENT_ACCESS_DENIED"


def test_admin_still_sees_all_documents(client, db, users, seed_refs):
    approved_payment_request = _create_approved_payment_request(client, db, users, seed_refs)
    draft_payment_request = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    approved_non_payment_request = _create_non_payment_request_document(db, users)

    response = client.get("/api/v1/documents", headers=auth_headers(str(users["admin"].id)))
    assert response.status_code == 200, response.text
    visible_ids = {item["id"] for item in response.json()}
    assert approved_payment_request["id"] in visible_ids
    assert draft_payment_request["id"] in visible_ids
    assert str(approved_non_payment_request.id) in visible_ids