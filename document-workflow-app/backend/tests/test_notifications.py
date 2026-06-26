from __future__ import annotations

from io import BytesIO

from app.modules.notifications.models import Notification, NotificationType
from tests.conftest import auth_headers, create_test_document, pending_task_for_document


def notification_payload(recipient_id, actor_id=None, document_id=None):
    return Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        type=NotificationType.DOCUMENT_SUBMITTED,
        title="Test notification",
        message="Test message",
        entity_type="document",
        entity_id=document_id,
        document_id=document_id,
        payload={"test": True},
    )


def notifications_for(client, user_id: str, **params):
    response = client.get("/api/v1/notifications/my", headers=auth_headers(user_id), params=params)
    assert response.status_code == 200, response.text
    return response.json()


def find_notification(client, user_id: str, notification_type: str, document_id: str):
    data = notifications_for(client, user_id, limit=100)
    return [
        item
        for item in data["items"]
        if item["type"] == notification_type and item["document_id"] == document_id
    ]


def test_missing_x_user_id_returns_401_for_notifications(client):
    response = client.get("/api/v1/notifications/my")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_user_can_get_own_notifications(client, db, users):
    notification = notification_payload(users["author"].id, actor_id=users["admin"].id)
    db.add(notification)
    db.commit()

    data = notifications_for(client, str(users["author"].id), limit=100)
    assert any(item["id"] == str(notification.id) for item in data["items"])


def test_user_cannot_mark_another_users_notification_as_read(client, db, users):
    notification = notification_payload(users["author"].id, actor_id=users["admin"].id)
    db.add(notification)
    db.commit()

    response = client.post(
        f"/api/v1/notifications/{notification.id}/read",
        headers=auth_headers(str(users["approver"].id)),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOTIFICATION_ACCESS_DENIED"


def test_unread_count_and_mark_one_as_read(client, db, users):
    notification = notification_payload(users["author"].id, actor_id=users["admin"].id)
    db.add(notification)
    db.commit()

    count_response = client.get("/api/v1/notifications/unread-count", headers=auth_headers(str(users["author"].id)))
    assert count_response.status_code == 200, count_response.text
    assert count_response.json()["unread_count"] >= 1

    read_response = client.post(
        f"/api/v1/notifications/{notification.id}/read",
        headers=auth_headers(str(users["author"].id)),
    )
    assert read_response.status_code == 200, read_response.text
    assert read_response.json() == {"status": "read"}

    db.expire_all()
    refreshed = db.get(Notification, notification.id)
    assert refreshed is not None
    assert refreshed.is_read is True
    assert refreshed.read_at is not None


def test_mark_all_as_read(client, db, users):
    db.add(notification_payload(users["author"].id, actor_id=users["admin"].id))
    db.add(notification_payload(users["author"].id, actor_id=users["admin"].id))
    db.commit()

    response = client.post("/api/v1/notifications/read-all", headers=auth_headers(str(users["author"].id)))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "read_all"
    assert response.json()["updated_count"] >= 2

    count_response = client.get("/api/v1/notifications/unread-count", headers=auth_headers(str(users["author"].id)))
    assert count_response.status_code == 200, count_response.text
    assert count_response.json()["unread_count"] == 0


def test_submit_document_creates_notification_for_approver(client, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)

    response = client.post(f"/api/v1/documents/{document['id']}/submit", headers=auth_headers(str(users["author"].id)))
    assert response.status_code == 200, response.text

    matches = find_notification(client, str(users["approver"].id), NotificationType.APPROVAL_TASK_CREATED, document["id"])
    assert matches
    assert matches[0]["task_id"]


def test_approve_task_creates_notification_for_document_author(client, db, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(f"/api/v1/documents/{document['id']}/submit", headers=auth_headers(str(users["author"].id)))
    assert submit_response.status_code == 200, submit_response.text
    db.expire_all()
    task = pending_task_for_document(db, document["id"])

    approve_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/approve",
        json={"comment": "approved"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert approve_response.status_code == 200, approve_response.text

    assert find_notification(client, str(users["author"].id), NotificationType.APPROVAL_TASK_APPROVED, document["id"])
    assert find_notification(client, str(users["author"].id), NotificationType.DOCUMENT_APPROVED, document["id"])


def test_reject_task_creates_notification_for_document_author(client, db, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(f"/api/v1/documents/{document['id']}/submit", headers=auth_headers(str(users["author"].id)))
    assert submit_response.status_code == 200, submit_response.text
    db.expire_all()
    task = pending_task_for_document(db, document["id"])

    reject_response = client.post(
        f"/api/v1/workflow/tasks/{task.id}/reject",
        json={"comment": "rejected"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert reject_response.status_code == 200, reject_response.text

    assert find_notification(client, str(users["author"].id), NotificationType.APPROVAL_TASK_REJECTED, document["id"])
    assert find_notification(client, str(users["author"].id), NotificationType.DOCUMENT_REJECTED, document["id"])


def test_comment_creates_notification_for_document_participant(client, db, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)
    submit_response = client.post(f"/api/v1/documents/{document['id']}/submit", headers=auth_headers(str(users["author"].id)))
    assert submit_response.status_code == 200, submit_response.text

    response = client.post(
        f"/api/v1/documents/{document['id']}/comments",
        json={"comment_text": "Please check this"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert response.status_code == 200, response.text

    assert find_notification(client, str(users["author"].id), NotificationType.DOCUMENT_COMMENT_CREATED, document["id"])


def test_file_upload_creates_notification_for_document_participant(client, users, seed_refs):
    document = create_test_document(client, str(users["author"].id), str(users["author"].id), seed_refs)

    response = client.post(
        f"/api/v1/documents/{document['id']}/files",
        headers=auth_headers(str(users["admin"].id)),
        data={"field_code": "invoiceFile"},
        files={"file": ("notice.pdf", BytesIO(b"hello"), "application/pdf")},
    )
    assert response.status_code == 200, response.text

    matches = find_notification(client, str(users["author"].id), NotificationType.DOCUMENT_FILE_UPLOADED, document["id"])
    assert matches
    assert matches[0]["payload"]["file_name"] == "notice.pdf"
