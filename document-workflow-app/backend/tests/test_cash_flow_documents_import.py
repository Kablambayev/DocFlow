from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select

from app.modules.documents.models import Document
from app.modules.users.models import User
from tests.conftest import auth_headers


def _accounting_admin_headers(db) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == "accounting_admin@example.com"))
    assert user is not None
    return auth_headers(str(user.id))


def _admin_headers(users) -> dict[str, str]:
    return auth_headers(str(users["admin"].id))


def _sample_item(*, external_id: str = "smoke-cash-flow-doc-001", source_document_type_1c: str = "ПлатежноеПоручениеИсходящее", amount: int = 1500000):
    return {
        "external_id": external_id,
        "source_document_type_1c": source_document_type_1c,
        "number": "000000123",
        "date": "2026-06-29",
        "posted_at": "2026-06-29T10:00:00+05:00",
        "organization": {"external_id": "ORG-001"},
        "counterparty": {"external_id": "CNT-001"},
        "contract": {"external_id": "CTR-ORG1-CNT1-142"},
        "currency": {"external_id": "CUR-KZT"},
        "amount": amount,
        "payment_purpose": "Оплата поставщику",
        "project": {"code": "ERP"},
        "cash_flow_item": {"external_id": "dds-supplier-payment"},
        "raw_data": {"one_c_ref": external_id},
    }


def _import_payload(items: list[dict]):
    return {"source_system": "1C", "items": items}


def _find_allocation(db, external_id: str) -> Document:
    row = db.scalar(
        select(Document).where(
            Document.data_json["source_system"].astext == "1C",
            Document.data_json["source_document_external_id"].astext == external_id,
        )
    )
    assert row is not None
    return row


def test_import_requires_auth_and_permission(client, db, users):
    payload = _import_payload([_sample_item()])

    no_auth = client.post("/api/v1/integration/1c/cash-flow-documents/import", json=payload)
    assert no_auth.status_code == 401

    no_permission = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=payload,
        headers=auth_headers(str(users["author"].id)),
    )
    assert no_permission.status_code == 403

    admin = client.post("/api/v1/integration/1c/cash-flow-documents/import", json=payload, headers=_admin_headers(users))
    assert admin.status_code == 200, admin.text


def test_import_validates_batch_and_document_type(client, db):
    too_large_items = [_sample_item(external_id=f"bulk-{index}") for index in range(1001)]
    too_large = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload(too_large_items),
        headers=_accounting_admin_headers(db),
    )
    assert too_large.status_code == 422
    assert too_large.json()["error"]["code"] == "IMPORT_BATCH_TOO_LARGE"

    unsupported = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload([_sample_item(external_id="unsupported-1", source_document_type_1c="НеизвестныйТип1С")]),
        headers=_accounting_admin_headers(db),
    )
    assert unsupported.status_code == 200, unsupported.text
    body = unsupported.json()
    assert body["skipped"] == 1
    assert body["errors"][0]["code"] == "UNSUPPORTED_CASH_FLOW_DOCUMENT_TYPE"


def test_import_creates_completed_and_needs_enrichment_allocations(client, db):
    completed_response = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload([_sample_item(external_id=f"completed-{uuid4().hex[:8]}")]),
        headers=_accounting_admin_headers(db),
    )
    assert completed_response.status_code == 200, completed_response.text
    completed_body = completed_response.json()
    assert completed_body["created"] == 1
    assert completed_body["completed"] == 1
    assert completed_body["needs_enrichment"] == 0

    missing_analytics_item = _sample_item(external_id=f"needs-{uuid4().hex[:8]}")
    missing_analytics_item["cash_flow_item"] = {"external_id": "missing-item"}
    needs_response = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload([missing_analytics_item]),
        headers=_accounting_admin_headers(db),
    )
    assert needs_response.status_code == 200, needs_response.text
    needs_body = needs_response.json()
    assert needs_body["created"] == 1
    assert needs_body["completed"] == 0
    assert needs_body["needs_enrichment"] == 1

    created = _find_allocation(db, missing_analytics_item["external_id"])
    assert created.data_json["allocation_status"] == "NeedsEnrichment"
    assert "cash_flow_item_id" in created.data_json["missing_required_fields"]


def test_reimport_updates_existing_document_without_duplicate_and_preserves_manual_fields(client, db):
    external_id = f"reimport-{uuid4().hex[:8]}"
    first = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload([_sample_item(external_id=external_id)]),
        headers=_accounting_admin_headers(db),
    )
    assert first.status_code == 200, first.text
    created = _find_allocation(db, external_id)
    original_id = created.id

    data_json = deepcopy(created.data_json)
    data_json["project_id"] = None
    data_json["cash_flow_item_id"] = str(uuid4())
    data_json["management_comment"] = "manual note"
    created.data_json = data_json
    db.commit()

    updated_item = _sample_item(external_id=external_id, amount=1700000)
    updated_item["project"] = {"code": "MAIN"}
    updated_item["cash_flow_item"] = {"external_id": "dds-supplier-payment"}
    second = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload([updated_item]),
        headers=_accounting_admin_headers(db),
    )
    assert second.status_code == 200, second.text
    assert second.json()["updated"] == 1

    refreshed = _find_allocation(db, external_id)
    assert refreshed.id == original_id
    assert refreshed.data_json["cash_flow_item_id"] == data_json["cash_flow_item_id"]
    assert refreshed.data_json["management_comment"] == "manual note"
    assert refreshed.data_json["project_id"] is not None
    assert str(refreshed.data_json["amount"]) == "1700000"


def test_reimport_completed_document_sets_source_changed_when_critical_source_changed(client, db):
    external_id = f"source-change-{uuid4().hex[:8]}"
    create_response = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload([_sample_item(external_id=external_id, amount=1500000)]),
        headers=_accounting_admin_headers(db),
    )
    assert create_response.status_code == 200, create_response.text
    document = _find_allocation(db, external_id)
    data_json = deepcopy(document.data_json)
    data_json["allocation_status"] = "Completed"
    document.data_json = data_json
    db.commit()

    changed_response = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload([_sample_item(external_id=external_id, amount=2500000)]),
        headers=_accounting_admin_headers(db),
    )
    assert changed_response.status_code == 200, changed_response.text
    refreshed = _find_allocation(db, external_id)
    assert refreshed.data_json["allocation_status"] == "Completed"
    assert refreshed.data_json["source_changed"] is True
