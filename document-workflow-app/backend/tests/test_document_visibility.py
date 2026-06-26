from __future__ import annotations

from tests.conftest import auth_headers, create_test_document


def test_admin_sees_seed_documents(client, users):
    response = client.get("/api/v1/documents", headers=auth_headers(str(users["admin"].id)))
    assert response.status_code == 200, response.text
    assert len(response.json()) >= 1


def test_author_document_list_contains_only_visible_documents(client, users):
    response = client.get("/api/v1/documents", headers=auth_headers(str(users["author"].id)))
    assert response.status_code == 200, response.text
    documents = response.json()
    assert documents
    assert all(document["author_id"] == str(users["author"].id) for document in documents)


def test_author_cannot_open_foreign_document_without_task(client, users, seed_refs):
    foreign_document = create_test_document(
        client,
        actor_id=str(users["admin"].id),
        author_id=str(users["approver"].id),
        seed_refs=seed_refs,
    )

    response = client.get(
        f"/api/v1/documents/{foreign_document['id']}",
        headers=auth_headers(str(users["author"].id)),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "DOCUMENT_ACCESS_DENIED"
