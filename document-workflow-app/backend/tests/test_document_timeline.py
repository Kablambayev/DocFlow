from __future__ import annotations

from tests.conftest import auth_headers, create_test_document


def test_document_timeline_returns_sorted_events(client, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    comment_response = client.post(
        f"/api/v1/documents/{document['id']}/comments",
        json={"comment_text": "Timeline comment"},
        headers=auth_headers(str(users["author"].id)),
    )
    assert comment_response.status_code == 200, comment_response.text

    response = client.get(f"/api/v1/documents/{document['id']}/timeline", headers=auth_headers(str(users["author"].id)))
    assert response.status_code == 200, response.text
    events = response.json()
    assert events
    assert any(item["type"] == "comment_added" for item in events)
    assert [item["created_at"] for item in events] == sorted(item["created_at"] for item in events)


def test_approval_timeline_returns_process_steps_tasks(client, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(f"/api/v1/documents/{document['id']}/submit", headers=auth_headers(str(users["author"].id)))
    assert submit_response.status_code == 200, submit_response.text

    response = client.get(f"/api/v1/documents/{document['id']}/approval-timeline", headers=auth_headers(str(users["author"].id)))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["process"]
    assert data["steps"]
    assert data["steps"][0]["tasks"]


def test_timeline_forbidden_without_document_access(client, users, seed_refs):
    foreign_document = create_test_document(client, str(users["admin"].id), str(users["approver"].id), seed_refs)
    response = client.get(
        f"/api/v1/documents/{foreign_document['id']}/timeline",
        headers=auth_headers(str(users["author"].id)),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "DOCUMENT_ACCESS_DENIED"
