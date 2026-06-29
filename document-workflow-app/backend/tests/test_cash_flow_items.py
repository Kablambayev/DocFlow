from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.modules.accounting.models import AccountingCashFlowItem
from app.modules.integration.log_models import IntegrationOperationLog
from tests.conftest import auth_headers


def test_accounting_admin_can_list_cash_flow_items(client, users):
    response = client.get("/api/v1/accounting/cash-flow-items", headers=auth_headers(str(users["accounting_admin"].id)))
    assert response.status_code == 200, response.text
    assert any(item["code"] == "DDS-001" for item in response.json())


def test_import_cash_flow_items_creates_records(client, users, db):
    external_id = f"dds-rent-payment-{uuid4().hex[:8]}"
    payload = {
        "source_system": "1C",
        "items": [
            {
                "external_id": external_id,
                "code": "DDS-900",
                "name": "Арендные платежи",
                "full_name": "Арендные платежи по офисам",
                "direction": "Outflow",
                "is_active": True,
                "raw_data": {"source": "test"},
            }
        ],
    }
    response = client.post(
        "/api/v1/integration/1c/cash-flow-items/import",
        json=payload,
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 1
    item = db.scalar(select(AccountingCashFlowItem).where(AccountingCashFlowItem.external_id == external_id))
    assert item is not None
    assert item.direction == "Outflow"


def test_reimport_cash_flow_items_updates_records(client, users, db):
    first_payload = {
        "source_system": "1C",
        "items": [{"external_id": "dds-bonus", "code": "DDS-910", "name": "Бонусы", "direction": "Both"}],
    }
    second_payload = {
        "source_system": "1C",
        "items": [{"external_id": "dds-bonus", "code": "DDS-910", "name": "Бонусы поставщиков", "direction": "Inflow"}],
    }
    first = client.post("/api/v1/integration/1c/cash-flow-items/import", json=first_payload, headers=auth_headers(str(users["accounting_admin"].id)))
    second = client.post("/api/v1/integration/1c/cash-flow-items/import", json=second_payload, headers=auth_headers(str(users["accounting_admin"].id)))
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["updated"] == 1
    item = db.scalar(select(AccountingCashFlowItem).where(AccountingCashFlowItem.external_id == "dds-bonus"))
    assert item is not None
    assert item.name == "Бонусы поставщиков"
    assert item.direction == "Inflow"


def test_invalid_cash_flow_item_returns_item_level_error(client, users):
    payload = {
        "source_system": "1C",
        "items": [{"external_id": "dds-invalid", "direction": "Outflow"}],
    }
    response = client.post(
        "/api/v1/integration/1c/cash-flow-items/import",
        json=payload,
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["skipped"] == 1
    assert body["errors"][0]["code"] == "VALIDATION_ERROR"


def test_cash_flow_items_import_writes_integration_log(client, users, db):
    payload = {
        "source_system": "1C",
        "items": [{"external_id": "dds-log-check", "name": "Проверка лога"}],
    }
    response = client.post(
        "/api/v1/integration/1c/cash-flow-items/import",
        json=payload,
        headers=auth_headers(str(users["accounting_admin"].id)),
    )
    assert response.status_code == 200, response.text
    log = db.scalar(
        select(IntegrationOperationLog)
        .where(IntegrationOperationLog.operation_type == "1c_import_cash_flow_items")
        .order_by(IntegrationOperationLog.created_at.desc())
    )
    assert log is not None
    assert log.direction == "Inbound"
    assert log.status == "Success"
