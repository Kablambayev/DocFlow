from __future__ import annotations

from tests.conftest import auth_headers, create_test_document, pending_task_for_document


def test_missing_x_user_id_returns_401_for_comments(client, users):
    response = client.get(f"/api/v1/documents/{users['author'].id}/comments")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_author_can_create_list_update_and_delete_own_comment(client, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    headers = auth_headers(str(users["author"].id))

    create_response = client.post(
        f"/api/v1/documents/{document['id']}/comments",
        json={"comment_text": "Please review"},
        headers=headers,
    )
    assert create_response.status_code == 200, create_response.text
    comment = create_response.json()
    assert comment["comment_type"] == "general"
    assert comment["author_name"]

    list_response = client.get(f"/api/v1/documents/{document['id']}/comments", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == comment["id"] for item in list_response.json())

    update_response = client.put(
        f"/api/v1/comments/{comment['id']}",
        json={"comment_text": "Updated comment"},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["comment_text"] == "Updated comment"

    delete_response = client.delete(f"/api/v1/comments/{comment['id']}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json() == {"status": "deleted"}


def test_user_without_document_access_cannot_read_comments(client, users, seed_refs):
    foreign_document = create_test_document(client, str(users["admin"].id), str(users["approver"].id), seed_refs)
    response = client.get(
        f"/api/v1/documents/{foreign_document['id']}/comments",
        headers=auth_headers(str(users["author"].id)),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "DOCUMENT_ACCESS_DENIED"


def test_user_cannot_edit_someone_else_comment(client, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    create_response = client.post(
        f"/api/v1/documents/{document['id']}/comments",
        json={"comment_text": "Author comment"},
        headers=auth_headers(str(users["author"].id)),
    )
    assert create_response.status_code == 200, create_response.text

    response = client.put(
        f"/api/v1/comments/{create_response.json()['id']}",
        json={"comment_text": "Approver edit"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert response.status_code == 403


def test_approver_can_comment_after_task_access(client, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(f"/api/v1/documents/{document['id']}/submit", headers=auth_headers(str(users["author"].id)))
    assert submit_response.status_code == 200, submit_response.text

    response = client.post(
        f"/api/v1/documents/{document['id']}/comments",
        json={"comment_text": "Approver comment"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert response.status_code == 200, response.text


def test_reject_requires_comment_and_creates_approval_comment(client, db, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(f"/api/v1/documents/{document['id']}/submit", headers=auth_headers(str(users["author"].id)))
    assert submit_response.status_code == 200, submit_response.text
    db.expire_all()
    task = pending_task_for_document(db, document["id"])

    no_comment_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/reject",
        json={"comment": ""},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert no_comment_response.status_code == 400
    assert no_comment_response.json()["error"]["code"] == "REJECT_COMMENT_REQUIRED"

    reject_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/reject",
        json={"comment": "Need more details"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert reject_response.status_code == 200, reject_response.text

    comments_response = client.get(f"/api/v1/documents/{document['id']}/comments", headers=auth_headers(str(users["author"].id)))
    assert comments_response.status_code == 200, comments_response.text
    approval_comments = [item for item in comments_response.json() if item["comment_type"] == "approval"]
    assert approval_comments
    assert approval_comments[0]["comment_text"] == "Need more details"

    edit_response = client.put(
        f"/api/v1/comments/{approval_comments[0]['id']}",
        json={"comment_text": "changed"},
        headers=auth_headers(str(users["admin"].id)),
    )
    assert edit_response.status_code == 403
    assert edit_response.json()["error"]["code"] == "COMMENT_CHANGE_FORBIDDEN"
