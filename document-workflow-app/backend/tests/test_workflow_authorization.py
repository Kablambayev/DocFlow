from __future__ import annotations

from tests.conftest import auth_headers, create_test_document, pending_task_for_document


def test_submit_task_and_approve_flow_keeps_rbac_enforced(client, db, users, seed_refs):
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
    assert submit_response.json()["approval_status"] == "OnApproval"

    tasks_response = client.get("/api/v1/workflow/tasks/my", headers=auth_headers(str(users["approver"].id)))
    assert tasks_response.status_code == 200, tasks_response.text
    tasks = tasks_response.json()
    task = next((item for item in tasks if item["document_id"] == document["id"]), None)
    assert task is not None

    db.expire_all()
    task_model = pending_task_for_document(db, document["id"])

    wrong_user_response = client.post(
        f"/api/v1/workflow/tasks/{task_model.id}/approve",
        json={"comment": "wrong user"},
        headers=auth_headers(str(users["admin"].id)),
    )
    assert wrong_user_response.status_code == 403
    assert wrong_user_response.json()["error"]["code"] == "TASK_ACCESS_DENIED"

    approve_response = client.post(
        f"/api/v1/workflow/tasks/{task_model.id}/approve",
        json={"comment": "approved"},
        headers=auth_headers(str(users["approver"].id)),
    )
    assert approve_response.status_code == 200, approve_response.text

    document_response = client.get(
        f"/api/v1/documents/{document['id']}",
        headers=auth_headers(str(users["approver"].id)),
    )
    assert document_response.status_code == 200, document_response.text
    assert document_response.json()["approval_status"] == "Approved"
