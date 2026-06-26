from __future__ import annotations

from tests.conftest import auth_headers


def error_code(response) -> str:
    return response.json()["error"]["code"]


def test_missing_x_user_id_returns_auth_required(client):
    for path in ["/api/v1/me", "/api/v1/documents"]:
        response = client.get(path)
        assert response.status_code == 401
        assert error_code(response) == "AUTH_REQUIRED"


def test_admin_can_access_rbac_and_admin_endpoints(client, users):
    headers = auth_headers(str(users["admin"].id))

    for path in [
        "/api/v1/me",
        "/api/v1/me/permissions",
        "/api/v1/users",
        "/api/v1/roles",
        "/api/v1/permissions",
        "/api/v1/document-types",
        "/api/v1/workflow/routes",
        "/api/v1/workflow/matrix-rules",
    ]:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text

    permissions = client.get("/api/v1/me/permissions", headers=headers).json()
    assert "admin.access" in permissions


def test_author_permissions(client, users):
    headers = auth_headers(str(users["author"].id))

    for path in ["/api/v1/me", "/api/v1/me/permissions", "/api/v1/documents", "/api/v1/document-types/active"]:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text

    for path in ["/api/v1/users", "/api/v1/roles", "/api/v1/workflow/routes", "/api/v1/workflow/matrix-rules"]:
        response = client.get(path, headers=headers)
        assert response.status_code == 403
        assert error_code(response) == "PERMISSION_DENIED"


def test_approver_permissions(client, users, seed_refs):
    headers = auth_headers(str(users["approver"].id))

    for path in ["/api/v1/me", "/api/v1/me/permissions", "/api/v1/workflow/tasks/my", "/api/v1/documents"]:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text

    invalid_document_type_payload = {"code": "test_forbidden", "name": "Forbidden", "description": None, "is_active": True}
    invalid_route_payload = {
        "document_type_id": str(seed_refs["document_type"].id),
        "code": "test_forbidden",
        "name": "Forbidden",
        "description": None,
        "is_active": True,
    }
    invalid_matrix_payload = {
        "document_type_id": str(seed_refs["document_type"].id),
        "priority": 999,
        "name": "Forbidden",
        "condition_json": {"operator": "and", "conditions": []},
        "route_id": str(seed_refs["route"].id),
        "is_active": True,
    }

    forbidden_requests = [
        ("get", "/api/v1/users", None),
        ("get", "/api/v1/roles", None),
        ("post", "/api/v1/document-types", invalid_document_type_payload),
        ("post", "/api/v1/workflow/routes", invalid_route_payload),
        ("post", "/api/v1/workflow/matrix-rules", invalid_matrix_payload),
    ]
    for method, path, payload in forbidden_requests:
        if payload is None:
            response = getattr(client, method)(path, headers=headers)
        else:
            response = getattr(client, method)(path, json=payload, headers=headers)
        assert response.status_code == 403
        assert error_code(response) == "PERMISSION_DENIED"
