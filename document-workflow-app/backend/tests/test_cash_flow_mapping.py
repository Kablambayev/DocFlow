from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.modules.cash_flow.mapping_models import CashFlowMappingRule
from app.modules.cash_flow.mapping_repository import CashFlowMappingRepository
from app.modules.cash_flow.mapping_service import CashFlowMappingService
from app.modules.document_types.models import DocumentType
from tests.conftest import auth_headers


def build_rule_payload(priority: int = 777, doc_type_1c: str = "ТестовыйДокумент1С", doc_type_code: str = "TestDocument"):
    return {
        "name": "Autotest mapping rule",
        "source_system": "1C",
        "source_document_type_1c": doc_type_1c,
        "source_document_type_code": doc_type_code,
        "cash_flow_direction": "Outflow",
        "target_document_type_code": "CashFlowAllocation",
        "priority": priority,
        "is_active": True,
        "fields": [
            {"target_field": "source_document_external_id", "mapping_type": "path", "source_path": "$.ref", "sort_order": 20},
            {"target_field": "cash_flow_direction", "mapping_type": "constant", "constant_value": "Outflow", "sort_order": 10},
            {
                "target_field": "organization_id",
                "mapping_type": "dictionary_lookup",
                "dictionary_type": "organization",
                "lookup_by": "external_id",
                "source_path": "$.organization.external_id",
                "sort_order": 30,
            },
            {
                "target_field": "currency_id",
                "mapping_type": "dictionary_lookup",
                "dictionary_type": "currency",
                "lookup_by": "external_id",
                "source_path": "$.currency.external_id",
                "sort_order": 40,
            },
            {
                "target_field": "cash_flow_item_id",
                "mapping_type": "dictionary_lookup",
                "dictionary_type": "cash_flow_item",
                "lookup_by": "external_id",
                "source_path": "$.cash_flow_item.external_id",
                "sort_order": 50,
            },
            {"target_field": "amount", "mapping_type": "path", "source_path": "$.amount", "sort_order": 60},
            {"target_field": "source_document_date", "mapping_type": "path", "source_path": "$.date", "sort_order": 70},
            {"target_field": "project_id", "mapping_type": "dictionary_lookup", "dictionary_type": "project", "lookup_by": "code", "source_path": "$.project.code", "sort_order": 80},
        ],
    }


def build_sample_payload():
    return {
        "ref": "1c-guid",
        "number": "000000123",
        "date": "2026-06-29",
        "posted_at": "2026-06-29T10:00:00+05:00",
        "organization": {"external_id": "ORG-001"},
        "counterparty": {"external_id": "CNT-001"},
        "contract": {"external_id": "CTR-ORG1-CNT1-142"},
        "currency": {"external_id": "CUR-KZT"},
        "amount": 1500000,
        "payment_purpose": "Оплата поставщику",
        "comment": "",
        "project": {"code": "ERP"},
        "cash_flow_item": {"external_id": "dds-supplier-payment"},
    }


def test_mapping_rules_require_auth_header(client):
    response = client.get("/api/v1/cash-flow/mapping-rules")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_user_without_permission_gets_403(client, users):
    response = client.get("/api/v1/cash-flow/mapping-rules", headers=auth_headers(str(users["author"].id)))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_accounting_admin_can_crud_mapping_rule(client, users):
    payload = build_rule_payload(priority=771, doc_type_1c=f"ТестовыйДокумент1С-{uuid4().hex[:6]}", doc_type_code=f"TestDocument-{uuid4().hex[:6]}")
    create_response = client.post("/api/v1/cash-flow/mapping-rules", json=payload, headers=auth_headers(str(users["accounting_admin"].id)))
    assert create_response.status_code == 200, create_response.text
    created = create_response.json()
    assert [field["sort_order"] for field in created["fields"]] == [10, 20, 30, 40, 50, 60, 70, 80]

    rule_id = created["id"]
    get_response = client.get(f"/api/v1/cash-flow/mapping-rules/{rule_id}", headers=auth_headers(str(users["accounting_admin"].id)))
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["fields"][0]["target_field"] == "cash_flow_direction"

    organization_field = next(field for field in created["fields"] if field["target_field"] == "organization_id")
    update_payload = {
        "name": "Autotest mapping rule updated",
        "fields": [
            {"id": organization_field["id"], "target_field": "organization_id", "mapping_type": "dictionary_lookup", "dictionary_type": "organization", "lookup_by": "external_id", "source_path": "$.organization.external_id", "sort_order": 5},
            {"target_field": "cash_flow_direction", "mapping_type": "constant", "constant_value": "Outflow", "sort_order": 10},
            {"target_field": "source_document_external_id", "mapping_type": "path", "source_path": "$.ref", "sort_order": 20},
        ],
    }
    update_response = client.put(
        f"/api/v1/cash-flow/mapping-rules/{rule_id}",
        json=update_payload,
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["name"] == "Autotest mapping rule updated"
    assert [field["sort_order"] for field in updated["fields"]] == [5, 10, 20]

    delete_response = client.delete(f"/api/v1/cash-flow/mapping-rules/{rule_id}", headers=auth_headers(str(users["accounting_admin"].id)))
    assert delete_response.status_code == 204


def test_admin_can_crud_mapping_rule(client, users):
    payload = build_rule_payload(priority=772, doc_type_1c=f"ТестовыйДокумент1С-{uuid4().hex[:6]}", doc_type_code=f"TestDocument-{uuid4().hex[:6]}")
    payload["name"] = "Admin mapping rule"
    create_response = client.post("/api/v1/cash-flow/mapping-rules", json=payload, headers=auth_headers(str(users["admin"].id)))
    assert create_response.status_code == 200, create_response.text
    rule_id = create_response.json()["id"]
    delete_response = client.delete(f"/api/v1/cash-flow/mapping-rules/{rule_id}", headers=auth_headers(str(users["admin"].id)))
    assert delete_response.status_code == 204


def test_mapping_engine_and_test_endpoint(client, users, db):
    service = CashFlowMappingService(CashFlowMappingRepository(db))
    created = client.post(
        "/api/v1/cash-flow/mapping-rules",
        json=build_rule_payload(priority=773, doc_type_1c=f"ТестовыйДокумент1С-{uuid4().hex[:6]}", doc_type_code=f"TestDocument-{uuid4().hex[:6]}"),
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert created.status_code == 200, created.text
    rule_id = created.json()["id"]

    result = service.apply_mapping_rule(rule_id=rule_id, source_payload=build_sample_payload())
    assert result.status == "Completed"
    assert result.mapped_data["amount"] == 1500000
    assert result.mapped_data["project_id"]
    assert result.mapped_data["organization_id"]
    assert result.mapped_data["currency_id"]
    assert result.mapped_data["cash_flow_item_id"]

    endpoint_response = client.post(
        f"/api/v1/cash-flow/mapping-rules/{rule_id}/test",
        json={"source_payload": build_sample_payload()},
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert endpoint_response.status_code == 200, endpoint_response.text
    body = endpoint_response.json()
    assert body["status"] == "Completed"
    assert body["mapped_data"]["source_document_external_id"] == "1c-guid"
    assert any(item["target_field"] == "organization_id" and item["status"] == "mapped" for item in body["field_results"])


def test_missing_required_field_produces_needs_enrichment(client, users, db):
    response = client.post(
        "/api/v1/cash-flow/mapping-rules",
        json=build_rule_payload(priority=774, doc_type_1c=f"ТестовыйДокумент1С-{uuid4().hex[:6]}", doc_type_code=f"TestDocument-{uuid4().hex[:6]}"),
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert response.status_code == 200, response.text
    service = CashFlowMappingService(CashFlowMappingRepository(db))
    payload = build_sample_payload()
    payload["cash_flow_item"] = {"external_id": "missing-item"}
    result = service.test_mapping_rule(response.json()["id"], payload)
    assert result.status == "NeedsEnrichment"
    assert "cash_flow_item_id" in result.missing_required_fields


def test_invalid_json_path_returns_missing_field_result(client, users, db):
    payload = build_rule_payload(priority=775, doc_type_1c=f"ТестовыйДокумент1С-{uuid4().hex[:6]}", doc_type_code=f"TestDocument-{uuid4().hex[:6]}")
    payload["fields"][0]["source_path"] = "$.missing.ref"
    response = client.post("/api/v1/cash-flow/mapping-rules", json=payload, headers=auth_headers(str(users["accounting_admin"].id)))
    assert response.status_code == 200, response.text
    service = CashFlowMappingService(CashFlowMappingRepository(db))
    result = service.test_mapping_rule(response.json()["id"], build_sample_payload())
    external_id_result = next(item for item in result.field_results if item.target_field == "source_document_external_id")
    assert external_id_result.status == "missing"


def test_seed_creates_cash_flow_allocation_document_type(db):
    item = db.scalar(select(DocumentType).where(DocumentType.code == "CashFlowAllocation"))
    assert item is not None
    assert item.name == "Разноска БДДС"


def test_seed_creates_six_default_mapping_rules(db):
    count = db.query(CashFlowMappingRule).filter(CashFlowMappingRule.target_document_type_code == "CashFlowAllocation").count()
    assert count >= 6


def test_default_outgoing_rule_maps_sample_json(seed_refs, db):
    rule = seed_refs["cash_flow_rule"]
    service = CashFlowMappingService(CashFlowMappingRepository(db))
    result = service.test_mapping_rule(rule.id, build_sample_payload())
    assert result.status == "Completed"
    assert result.mapped_data["source_document_type"] == "PaymentOrderOutgoing"
    assert result.mapped_data["cash_flow_direction"] == "Outflow"
