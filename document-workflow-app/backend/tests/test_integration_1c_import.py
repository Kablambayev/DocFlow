from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.modules.accounting.models import (
    AccountingCounterparty,
    AccountingCounterpartyContract,
    AccountingCurrency,
    AccountingExpenseItem,
    AccountingOrganization,
)
from app.modules.users.models import User
from tests.conftest import auth_headers


def _accounting_admin_headers(db) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == "accounting_admin@example.com"))
    assert user is not None
    return auth_headers(str(user.id))


def test_import_permissions(client, db, users):
    payload = {"items": []}

    no_auth = client.post("/api/v1/integration/1c/organizations/import", json=payload)
    assert no_auth.status_code == 401
    assert no_auth.json()["error"]["code"] == "AUTH_REQUIRED"

    no_permission = client.post(
        "/api/v1/integration/1c/organizations/import",
        json=payload,
        headers=auth_headers(str(users["author"].id)),
    )
    assert no_permission.status_code == 403
    assert no_permission.json()["error"]["code"] == "PERMISSION_DENIED"

    admin_ok = client.post(
        "/api/v1/integration/1c/organizations/import",
        json=payload,
        headers=auth_headers(str(users["admin"].id)),
    )
    assert admin_ok.status_code == 200

    accounting_admin_ok = client.post(
        "/api/v1/integration/1c/organizations/import",
        json=payload,
        headers=_accounting_admin_headers(db),
    )
    assert accounting_admin_ok.status_code == 200


def test_organizations_import_create_reimport_update_and_validation_error(client, db):
    headers = _accounting_admin_headers(db)
    external_id = f"org-intg-{uuid4().hex[:8]}"

    first = client.post(
        "/api/v1/integration/1c/organizations/import",
        json={
            "source_system": "1C",
            "items": [
                {
                    "external_id": external_id,
                    "code": "ORG-INTG-1",
                    "name": "Integration Org",
                    "full_name": "Integration Organization",
                    "is_active": True,
                    "raw_data": {"bin": "123"},
                }
            ],
        },
        headers=headers,
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["created"] == 1
    assert first_body["updated"] == 0

    second = client.post(
        "/api/v1/integration/1c/organizations/import",
        json={
            "source_system": "1C",
            "items": [
                {
                    "external_id": external_id,
                    "code": "ORG-INTG-1",
                    "name": "Integration Org Updated",
                    "full_name": "Integration Organization Updated",
                    "is_active": True,
                    "raw_data": {"bin": "456"},
                }
            ],
        },
        headers=headers,
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["created"] == 0
    assert second_body["updated"] == 1

    db_item = db.scalar(
        select(AccountingOrganization).where(
            AccountingOrganization.source_system == "1C",
            AccountingOrganization.external_id == external_id,
        )
    )
    assert db_item is not None
    assert db_item.name == "Integration Org Updated"

    mixed = client.post(
        "/api/v1/integration/1c/organizations/import",
        json={
            "source_system": "1C",
            "items": [
                {"external_id": f"org-intg-{uuid4().hex[:8]}", "name": "Valid Org"},
                {"external_id": f"org-intg-{uuid4().hex[:8]}"},
            ],
        },
        headers=headers,
    )
    assert mixed.status_code == 200, mixed.text
    mixed_body = mixed.json()
    assert mixed_body["received"] == 2
    assert mixed_body["created"] == 1
    assert mixed_body["skipped"] == 1
    assert mixed_body["errors"][0]["code"] == "VALIDATION_ERROR"


def test_counterparties_import_create_and_update(client, db):
    headers = _accounting_admin_headers(db)
    external_id = f"cnt-intg-{uuid4().hex[:8]}"

    created = client.post(
        "/api/v1/integration/1c/counterparties/import",
        json={
            "items": [
                {
                    "external_id": external_id,
                    "code": "CNT-INTG-1",
                    "name": "Counterparty One",
                    "bin_iin": "990140000001",
                }
            ]
        },
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["created"] == 1

    updated = client.post(
        "/api/v1/integration/1c/counterparties/import",
        json={
            "items": [
                {
                    "external_id": external_id,
                    "code": "CNT-INTG-1",
                    "name": "Counterparty One Updated",
                    "bin_iin": "990140000002",
                }
            ]
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["updated"] == 1

    item = db.scalar(
        select(AccountingCounterparty).where(
            AccountingCounterparty.source_system == "1C",
            AccountingCounterparty.external_id == external_id,
        )
    )
    assert item is not None
    assert item.name == "Counterparty One Updated"


def test_counterparties_import_empty_name_is_partial_success(client, db):
    response = client.post(
        "/api/v1/integration/1c/counterparties/import",
        json={
            "source_system": "1C",
            "items": [
                {
                    "external_id": f"cp-valid-{uuid4().hex[:8]}",
                    "code": f"CP-{uuid4().hex[:4]}",
                    "name": "Valid Counterparty",
                },
                {
                    "external_id": f"cp-invalid-{uuid4().hex[:8]}",
                    "code": f"CP-{uuid4().hex[:4]}",
                    "name": "",
                },
            ],
        },
        headers=_accounting_admin_headers(db),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 1
    assert body["skipped"] == 1
    assert body["errors"][0]["code"] == "VALIDATION_ERROR"


def test_currencies_import_create_and_conflict_error(client, db):
    headers = _accounting_admin_headers(db)
    external_id = f"cur-intg-{uuid4().hex[:8]}"
    code = f"T{uuid4().hex[:4].upper()}"

    created = client.post(
        "/api/v1/integration/1c/currencies/import",
        json={
            "items": [
                {
                    "external_id": external_id,
                    "code": code,
                    "name": "Test Currency",
                }
            ]
        },
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["created"] == 1

    conflict = client.post(
        "/api/v1/integration/1c/currencies/import",
        json={
            "items": [
                {
                    "external_id": f"cur-intg-{uuid4().hex[:8]}",
                    "code": code,
                    "name": "Another Currency",
                }
            ]
        },
        headers=headers,
    )
    assert conflict.status_code == 200
    body = conflict.json()
    assert body["skipped"] == 1
    assert body["errors"][0]["code"] == "CURRENCY_CODE_CONFLICT"


def test_expense_items_import_and_deactivation(client, db):
    headers = _accounting_admin_headers(db)
    external_id = f"exp-intg-{uuid4().hex[:8]}"

    create = client.post(
        "/api/v1/integration/1c/expense-items/import",
        json={"items": [{"external_id": external_id, "name": "Expense A", "is_active": True}]},
        headers=headers,
    )
    assert create.status_code == 200
    assert create.json()["created"] == 1

    deactivate = client.post(
        "/api/v1/integration/1c/expense-items/import",
        json={"items": [{"external_id": external_id, "name": "Expense A", "is_active": False}]},
        headers=headers,
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["updated"] == 1

    item = db.scalar(
        select(AccountingExpenseItem).where(
            AccountingExpenseItem.source_system == "1C",
            AccountingExpenseItem.external_id == external_id,
        )
    )
    assert item is not None
    assert item.is_active is False


def test_contracts_import_resolve_dependencies_and_reimport_update(client, db):
    headers = _accounting_admin_headers(db)
    source = f"1C-INTG-{uuid4().hex[:6]}"

    org_external = f"org-{uuid4().hex[:8]}"
    cp_external = f"cp-{uuid4().hex[:8]}"
    cur_external = f"cur-{uuid4().hex[:8]}"
    contract_external = f"ctr-{uuid4().hex[:8]}"

    assert client.post(
        "/api/v1/integration/1c/organizations/import",
        json={"source_system": source, "items": [{"external_id": org_external, "name": "Org Intg"}]},
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/api/v1/integration/1c/counterparties/import",
        json={"source_system": source, "items": [{"external_id": cp_external, "name": "Counterparty Intg"}]},
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/api/v1/integration/1c/currencies/import",
        json={
            "source_system": source,
            "items": [{"external_id": cur_external, "code": f"I{uuid4().hex[:4].upper()}", "name": "Currency Intg"}],
        },
        headers=headers,
    ).status_code == 200

    created = client.post(
        "/api/v1/integration/1c/counterparty-contracts/import",
        json={
            "source_system": source,
            "items": [
                {
                    "external_id": contract_external,
                    "organization_external_id": org_external,
                    "counterparty_external_id": cp_external,
                    "currency_external_id": cur_external,
                    "name": "Contract A",
                    "number": "42-A",
                    "contract_date": "2026-01-15",
                }
            ],
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    assert created.json()["created"] == 1

    updated = client.post(
        "/api/v1/integration/1c/counterparty-contracts/import",
        json={
            "source_system": source,
            "items": [
                {
                    "external_id": contract_external,
                    "organization_external_id": org_external,
                    "counterparty_external_id": cp_external,
                    "currency_external_id": cur_external,
                    "name": "Contract A Updated",
                    "number": "42-B",
                    "contract_date": "2026-02-20",
                }
            ],
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["updated"] == 1

    contract = db.scalar(
        select(AccountingCounterpartyContract).where(
            AccountingCounterpartyContract.source_system == source,
            AccountingCounterpartyContract.external_id == contract_external,
        )
    )
    assert contract is not None
    assert contract.name == "Contract A Updated"
    assert contract.number == "42-B"


def test_contracts_import_missing_references_errors(client, db):
    headers = _accounting_admin_headers(db)
    source = f"1C-INTG-{uuid4().hex[:6]}"

    org_external = f"org-{uuid4().hex[:8]}"
    cp_external = f"cp-{uuid4().hex[:8]}"
    cur_external = f"cur-{uuid4().hex[:8]}"

    assert client.post(
        "/api/v1/integration/1c/organizations/import",
        json={"source_system": source, "items": [{"external_id": org_external, "name": "Org Intg"}]},
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/api/v1/integration/1c/counterparties/import",
        json={"source_system": source, "items": [{"external_id": cp_external, "name": "Counterparty Intg"}]},
        headers=headers,
    ).status_code == 200

    missing_org = client.post(
        "/api/v1/integration/1c/counterparty-contracts/import",
        json={
            "source_system": source,
            "items": [
                {
                    "external_id": f"ctr-{uuid4().hex[:8]}",
                    "organization_external_id": "missing-org",
                    "counterparty_external_id": cp_external,
                    "name": "Contract Missing Org",
                }
            ],
        },
        headers=headers,
    )
    assert missing_org.status_code == 200
    assert missing_org.json()["errors"][0]["code"] == "ORGANIZATION_NOT_FOUND"

    missing_cp = client.post(
        "/api/v1/integration/1c/counterparty-contracts/import",
        json={
            "source_system": source,
            "items": [
                {
                    "external_id": f"ctr-{uuid4().hex[:8]}",
                    "organization_external_id": org_external,
                    "counterparty_external_id": "missing-cp",
                    "name": "Contract Missing CP",
                }
            ],
        },
        headers=headers,
    )
    assert missing_cp.status_code == 200
    assert missing_cp.json()["errors"][0]["code"] == "COUNTERPARTY_NOT_FOUND"

    missing_currency = client.post(
        "/api/v1/integration/1c/counterparty-contracts/import",
        json={
            "source_system": source,
            "items": [
                {
                    "external_id": f"ctr-{uuid4().hex[:8]}",
                    "organization_external_id": org_external,
                    "counterparty_external_id": cp_external,
                    "currency_external_id": "missing-cur",
                    "name": "Contract Missing Cur",
                }
            ],
        },
        headers=headers,
    )
    assert missing_currency.status_code == 200
    assert missing_currency.json()["errors"][0]["code"] == "CURRENCY_NOT_FOUND"

    assert client.post(
        "/api/v1/integration/1c/currencies/import",
        json={"source_system": source, "items": [{"external_id": cur_external, "code": f"X{uuid4().hex[:4].upper()}", "name": "Cur"}]},
        headers=headers,
    ).status_code == 200


def test_partial_success_and_batch_limit(client, db):
    headers = _accounting_admin_headers(db)

    partial = client.post(
        "/api/v1/integration/1c/organizations/import",
        json={
            "items": [
                {"external_id": f"org-{uuid4().hex[:8]}", "name": "Valid"},
                {"external_id": f"org-{uuid4().hex[:8]}"},
                {"name": "Missing external"},
            ]
        },
        headers=headers,
    )
    assert partial.status_code == 200
    body = partial.json()
    assert body["received"] == 3
    assert body["created"] == 1
    assert body["skipped"] == 2
    assert len(body["errors"]) == 2

    too_large = client.post(
        "/api/v1/integration/1c/organizations/import",
        json={"items": [{"external_id": f"org-{index}", "name": "X"} for index in range(1001)]},
        headers=headers,
    )
    assert too_large.status_code == 422
    error = too_large.json()["error"]
    assert error["code"] == "IMPORT_BATCH_TOO_LARGE"


def test_contract_filter_still_works_by_internal_ids(client, db):
    headers = _accounting_admin_headers(db)
    source = f"1C-INTG-{uuid4().hex[:6]}"

    org_external = f"org-{uuid4().hex[:8]}"
    cp_external = f"cp-{uuid4().hex[:8]}"
    cur_external = f"cur-{uuid4().hex[:8]}"
    contract_external = f"ctr-{uuid4().hex[:8]}"

    assert client.post(
        "/api/v1/integration/1c/organizations/import",
        json={"source_system": source, "items": [{"external_id": org_external, "name": "Org Filter"}]},
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/api/v1/integration/1c/counterparties/import",
        json={"source_system": source, "items": [{"external_id": cp_external, "name": "CP Filter"}]},
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/api/v1/integration/1c/currencies/import",
        json={
            "source_system": source,
            "items": [{"external_id": cur_external, "code": f"F{uuid4().hex[:4].upper()}", "name": "Cur Filter"}],
        },
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/api/v1/integration/1c/counterparty-contracts/import",
        json={
            "source_system": source,
            "items": [
                {
                    "external_id": contract_external,
                    "organization_external_id": org_external,
                    "counterparty_external_id": cp_external,
                    "currency_external_id": cur_external,
                    "name": "Contract Filter",
                }
            ],
        },
        headers=headers,
    ).status_code == 200

    org = db.scalar(
        select(AccountingOrganization).where(
            AccountingOrganization.source_system == source,
            AccountingOrganization.external_id == org_external,
        )
    )
    cp = db.scalar(
        select(AccountingCounterparty).where(
            AccountingCounterparty.source_system == source,
            AccountingCounterparty.external_id == cp_external,
        )
    )
    assert org is not None and cp is not None

    filtered = client.get(
        "/api/v1/accounting/counterparty-contracts",
        params={"organization_id": str(org.id), "counterparty_id": str(cp.id)},
        headers=headers,
    )
    assert filtered.status_code == 200
    data = filtered.json()
    assert any(item["name"] == "Contract Filter" for item in data)
