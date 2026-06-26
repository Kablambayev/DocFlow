from __future__ import annotations

from uuid import uuid4

from tests.conftest import auth_headers


def test_accounting_read_endpoints_require_permission(client, users):
    admin_headers = auth_headers(str(users["admin"].id))
    author_headers = auth_headers(str(users["author"].id))

    read_paths = [
        "/api/v1/accounting/organizations",
        "/api/v1/accounting/counterparties",
        "/api/v1/accounting/currencies",
        "/api/v1/accounting/expense-items",
        "/api/v1/accounting/cash-flow-operation-types",
        "/api/v1/accounting/projects",
    ]

    for path in read_paths:
        response = client.get(path, headers=author_headers)
        assert response.status_code == 200, response.text

    create_payload = {"code": f"CFOT-{uuid4().hex[:8]}", "name": "Autotest CFOT"}

    forbidden = client.post("/api/v1/accounting/cash-flow-operation-types", json=create_payload, headers=author_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "PERMISSION_DENIED"

    allowed = client.post("/api/v1/accounting/cash-flow-operation-types", json=create_payload, headers=admin_headers)
    assert allowed.status_code == 200, allowed.text


def test_counterparty_contracts_filter_by_org_and_counterparty(client, users):
    headers = auth_headers(str(users["admin"].id))

    organizations = client.get("/api/v1/accounting/organizations", headers=headers)
    counterparties = client.get("/api/v1/accounting/counterparties", headers=headers)
    assert organizations.status_code == 200, organizations.text
    assert counterparties.status_code == 200, counterparties.text

    organization_id = organizations.json()[0]["id"]
    counterparty_id = counterparties.json()[0]["id"]

    no_filter = client.get("/api/v1/accounting/counterparty-contracts", headers=headers)
    assert no_filter.status_code == 200, no_filter.text
    assert no_filter.json() == []

    filtered = client.get(
        "/api/v1/accounting/counterparty-contracts",
        params={"organization_id": organization_id, "counterparty_id": counterparty_id},
        headers=headers,
    )
    assert filtered.status_code == 200, filtered.text

    for item in filtered.json():
        assert item["organization_id"] == organization_id
        assert item["counterparty_id"] == counterparty_id


def test_local_dictionaries_crud_and_soft_delete(client, users):
    headers = auth_headers(str(users["admin"].id))
    suffix = uuid4().hex[:8]

    operation_payload = {
        "code": f"CFOT-{suffix}",
        "name": "Автотест операция",
        "description": "Created by test",
        "sort_order": 777,
    }
    operation_created = client.post("/api/v1/accounting/cash-flow-operation-types", json=operation_payload, headers=headers)
    assert operation_created.status_code == 200, operation_created.text
    operation_id = operation_created.json()["id"]

    operation_updated = client.put(
        f"/api/v1/accounting/cash-flow-operation-types/{operation_id}",
        json={"name": "Автотест операция updated", "sort_order": 778},
        headers=headers,
    )
    assert operation_updated.status_code == 200, operation_updated.text
    assert operation_updated.json()["name"] == "Автотест операция updated"

    operation_deleted = client.delete(f"/api/v1/accounting/cash-flow-operation-types/{operation_id}", headers=headers)
    assert operation_deleted.status_code == 200, operation_deleted.text
    assert operation_deleted.json()["is_active"] is False

    operation_active_list = client.get(
        "/api/v1/accounting/cash-flow-operation-types",
        params={"search": f"CFOT-{suffix}", "is_active": True},
        headers=headers,
    )
    assert operation_active_list.status_code == 200, operation_active_list.text
    assert operation_active_list.json() == []

    project_payload = {
        "code": f"PRJ-{suffix}",
        "name": "Автотест проект",
        "description": "Created by test",
    }
    project_created = client.post("/api/v1/accounting/projects", json=project_payload, headers=headers)
    assert project_created.status_code == 200, project_created.text
    project_id = project_created.json()["id"]

    project_updated = client.put(
        f"/api/v1/accounting/projects/{project_id}",
        json={"name": "Автотест проект updated"},
        headers=headers,
    )
    assert project_updated.status_code == 200, project_updated.text
    assert project_updated.json()["name"] == "Автотест проект updated"

    project_deleted = client.delete(f"/api/v1/accounting/projects/{project_id}", headers=headers)
    assert project_deleted.status_code == 200, project_deleted.text
    assert project_deleted.json()["is_active"] is False

    project_active_list = client.get(
        "/api/v1/accounting/projects",
        params={"search": f"PRJ-{suffix}", "is_active": True},
        headers=headers,
    )
    assert project_active_list.status_code == 200, project_active_list.text
    assert project_active_list.json() == []
