from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.modules.accounting.models import AccountingCashFlowItem
from app.modules.documents.models import Document
from app.modules.users.models import User
from tests.conftest import auth_headers
from tests.test_cash_flow_documents_import import _accounting_admin_headers, _import_payload, _sample_item


def _import_one_allocation(client, db, *, external_id: str, amount: int = 1500000, cash_flow_item_external_id: str = "dds-supplier-payment") -> str:
    item = _sample_item(external_id=external_id, amount=amount)
    item["cash_flow_item"] = {"external_id": cash_flow_item_external_id}
    response = client.post(
        "/api/v1/integration/1c/cash-flow-documents/import",
        json=_import_payload([item]),
        headers=_accounting_admin_headers(db),
    )
    assert response.status_code == 200, response.text
    document = db.scalar(select(Document).where(Document.data_json["source_document_external_id"].astext == external_id))
    assert document is not None
    return str(document.id)


def test_allocations_registry_requires_permission(client, users):
    no_auth = client.get("/api/v1/cash-flow/allocations")
    assert no_auth.status_code == 401

    no_permission = client.get("/api/v1/cash-flow/allocations", headers=auth_headers(str(users["author"].id)))
    assert no_permission.status_code == 403


def test_allocations_registry_filters_and_detail(client, db):
    doc_id = _import_one_allocation(client, db, external_id=f"alloc-{uuid4().hex[:8]}")

    list_response = client.get(
        "/api/v1/cash-flow/allocations",
        params={"allocation_status": "Completed", "cash_flow_direction": "Outflow", "search": "000000123"},
        headers=_accounting_admin_headers(db),
    )
    assert list_response.status_code == 200, list_response.text
    body = list_response.json()
    assert body["total"] >= 1
    assert any(item["document_id"] == doc_id for item in body["items"])

    detail_response = client.get(f"/api/v1/cash-flow/allocations/{doc_id}", headers=_accounting_admin_headers(db))
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["raw_source_payload"]["external_id"]
    assert detail["mapping_rule_id"]


def test_allocations_update_complete_ignore_reopen(client, db):
    doc_id = _import_one_allocation(client, db, external_id=f"alloc-action-{uuid4().hex[:8]}", cash_flow_item_external_id="missing-item")

    initial_detail = client.get(f"/api/v1/cash-flow/allocations/{doc_id}", headers=_accounting_admin_headers(db))
    assert initial_detail.status_code == 200
    assert initial_detail.json()["allocation_status"] == "NeedsEnrichment"

    update_response = client.put(
        f"/api/v1/cash-flow/allocations/{doc_id}",
        json={"management_comment": "filled manually"},
        headers=_accounting_admin_headers(db),
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["management_comment"] == "filled manually"

    complete_fail = client.post(f"/api/v1/cash-flow/allocations/{doc_id}/complete", headers=_accounting_admin_headers(db))
    assert complete_fail.status_code == 409
    assert complete_fail.json()["error"]["code"] == "CASH_FLOW_ALLOCATION_REQUIRED_FIELDS_MISSING"

    cash_flow_item = db.scalar(select(AccountingCashFlowItem).where(AccountingCashFlowItem.external_id == "dds-supplier-payment"))
    assert cash_flow_item is not None
    cash_flow_item_id = str(cash_flow_item.id)

    fill_response = client.put(
        f"/api/v1/cash-flow/allocations/{doc_id}",
        json={"cash_flow_item_id": cash_flow_item_id},
        headers=_accounting_admin_headers(db),
    )
    assert fill_response.status_code == 200, fill_response.text

    complete_ok = client.post(f"/api/v1/cash-flow/allocations/{doc_id}/complete", headers=_accounting_admin_headers(db))
    assert complete_ok.status_code == 200, complete_ok.text
    assert complete_ok.json()["item"]["allocation_status"] == "Completed"

    ignore_ok = client.post(f"/api/v1/cash-flow/allocations/{doc_id}/ignore", headers=_accounting_admin_headers(db))
    assert ignore_ok.status_code == 200, ignore_ok.text
    assert ignore_ok.json()["item"]["allocation_status"] == "Ignored"

    reopen_ok = client.post(f"/api/v1/cash-flow/allocations/{doc_id}/reopen", headers=_accounting_admin_headers(db))
    assert reopen_ok.status_code == 200, reopen_ok.text
    assert reopen_ok.json()["item"]["allocation_status"] == "NeedsEnrichment"


def test_allocations_metrics_endpoint(client, db):
    _import_one_allocation(client, db, external_id=f"metrics-{uuid4().hex[:8]}")
    metrics_response = client.get("/api/v1/cash-flow/allocations/metrics", headers=_accounting_admin_headers(db))
    assert metrics_response.status_code == 200, metrics_response.text
    metrics = metrics_response.json()
    assert set(metrics.keys()) == {"needs_enrichment", "completed", "ignored", "source_changed"}
