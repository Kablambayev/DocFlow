from __future__ import annotations

from io import BytesIO

from app.core.config import settings
from tests.conftest import auth_headers, create_test_document, pending_task_for_document


def upload_file(client, document_id: str, user_id: str, filename: str = "invoice.pdf", content: bytes = b"hello"):
    return client.post(
        f"/api/v1/documents/{document_id}/files",
        headers=auth_headers(user_id),
        data={"field_code": "invoiceFile"},
        files={"file": (filename, BytesIO(content), "application/pdf")},
    )


def create_approved_document(client, db, users, seed_refs) -> dict:
    document = create_test_document(
        client,
        actor_id=str(users["author"].id),
        author_id=str(users["author"].id),
        seed_refs=seed_refs,
    )
    submit_response = client.post(
        f"/api/v1/documents/{document['id']}/submit",
        headers=auth_headers(str(users["author"].id)),
    )
    assert submit_response.status_code == 200, submit_response.text

    db.expire_all()
    task = pending_task_for_document(db, document["id"])
    approve_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/approve",
        json={"comment": "approved for file test"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert approve_response.status_code == 200, approve_response.text
    return document


def test_missing_x_user_id_returns_401_for_files(client, users):
    response = client.get(f"/api/v1/documents/{users['author'].id}/files")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_author_can_upload_list_download_and_delete_file_in_draft(client, users, seed_refs):
    document = create_test_document(
        client,
        actor_id=str(users["author"].id),
        author_id=str(users["author"].id),
        seed_refs=seed_refs,
    )
    author_id = str(users["author"].id)

    upload_response = upload_file(client, document["id"], author_id)
    assert upload_response.status_code == 200, upload_response.text
    uploaded = upload_response.json()
    assert uploaded["file_name"] == "invoice.pdf"
    assert uploaded["field_code"] == "invoiceFile"
    assert uploaded["size_bytes"] == 5

    list_response = client.get(f"/api/v1/documents/{document['id']}/files", headers=auth_headers(author_id))
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == uploaded["id"] for item in list_response.json())

    download_response = client.get(f"/api/v1/files/{uploaded['id']}/download", headers=auth_headers(author_id))
    assert download_response.status_code == 200, download_response.text
    assert download_response.content == b"hello"
    assert "invoice.pdf" in download_response.headers["content-disposition"]

    delete_response = client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers(author_id))
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json() == {"status": "deleted"}

    list_after_delete = client.get(f"/api/v1/documents/{document['id']}/files", headers=auth_headers(author_id))
    assert list_after_delete.status_code == 200, list_after_delete.text
    assert all(item["id"] != uploaded["id"] for item in list_after_delete.json())


def test_approver_can_read_and_download_file_only_after_task_access(client, db, users, seed_refs):
    document = create_test_document(
        client,
        actor_id=str(users["author"].id),
        author_id=str(users["author"].id),
        seed_refs=seed_refs,
    )
    upload_response = upload_file(client, document["id"], str(users["author"].id))
    assert upload_response.status_code == 200, upload_response.text
    uploaded = upload_response.json()

    approver_headers = auth_headers(str(users["approver"].id))
    before_task_response = client.get(f"/api/v1/documents/{document['id']}/files", headers=approver_headers)
    assert before_task_response.status_code == 403
    assert before_task_response.json()["error"]["code"] == "DOCUMENT_ACCESS_DENIED"

    submit_response = client.post(
        f"/api/v1/documents/{document['id']}/submit",
        headers=auth_headers(str(users["author"].id)),
    )
    assert submit_response.status_code == 200, submit_response.text

    list_response = client.get(f"/api/v1/documents/{document['id']}/files", headers=approver_headers)
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == uploaded["id"] for item in list_response.json())

    download_response = client.get(f"/api/v1/files/{uploaded['id']}/download", headers=approver_headers)
    assert download_response.status_code == 200, download_response.text
    assert download_response.content == b"hello"


def test_approver_cannot_upload(client, users, seed_refs):
    document = create_test_document(
        client,
        actor_id=str(users["author"].id),
        author_id=str(users["author"].id),
        seed_refs=seed_refs,
    )
    response = upload_file(client, document["id"], str(users["approver"].id))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_author_cannot_upload_to_approved_document(client, db, users, seed_refs):
    document = create_approved_document(client, db, users, seed_refs)
    response = upload_file(client, document["id"], str(users["author"].id))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DOCUMENT_FILE_MUTATION_FORBIDDEN"


def test_file_extension_restriction(client, users, seed_refs):
    document = create_test_document(
        client,
        actor_id=str(users["author"].id),
        author_id=str(users["author"].id),
        seed_refs=seed_refs,
    )
    response = upload_file(client, document["id"], str(users["author"].id), filename="payload.exe")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FILE_EXTENSION_NOT_ALLOWED"


def test_file_too_large_restriction(client, monkeypatch, users, seed_refs):
    document = create_test_document(
        client,
        actor_id=str(users["author"].id),
        author_id=str(users["author"].id),
        seed_refs=seed_refs,
    )
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    response = upload_file(client, document["id"], str(users["author"].id), content=b"x")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
