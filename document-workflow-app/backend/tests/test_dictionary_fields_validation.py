from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.modules.accounting.models import (
    AccountingCashFlowOperationType,
    AccountingCounterparty,
    AccountingCounterpartyContract,
    AccountingCurrency,
    AccountingExpenseItem,
    AccountingOrganization,
    AccountingProject,
)
from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from tests.conftest import auth_headers


def _payment_request_version_with_management_accounting(db) -> tuple[str, str]:
    document_type = db.scalar(select(DocumentType).where(DocumentType.code == "PaymentRequest"))
    assert document_type is not None

    versions = list(
        db.scalars(
            select(DocumentTypeVersion)
            .where(
                DocumentTypeVersion.document_type_id == document_type.id,
                DocumentTypeVersion.status == VersionStatus.PUBLISHED,
            )
            .order_by(DocumentTypeVersion.version_number.desc())
        )
    )
    assert versions, "Published PaymentRequest version is missing"

    for version in versions:
        sections = version.schema_json.get("sections", []) if isinstance(version.schema_json, dict) else []
        for section in sections:
            if section.get("code") != "management_accounting":
                continue
            fields = section.get("fields", []) if isinstance(section.get("fields"), list) else []
            field_codes = {field.get("code") for field in fields if isinstance(field, dict)}
            if {"organization_id", "counterparty_id", "contract_id", "project_id"}.issubset(field_codes):
                return str(document_type.id), str(version.id)

    raise AssertionError("No published PaymentRequest version with management accounting dictionary fields")


def _base_payload(document_type_id: str, document_type_version_id: str, author_id: str) -> dict:
    unique = f"DICT-{uuid4().hex[:10]}"
    return {
        "document_type_id": document_type_id,
        "document_type_version_id": document_type_version_id,
        "number": unique,
        "document_date": datetime.now(timezone.utc).isoformat(),
        "author_id": author_id,
        "organization_id": None,
        "department_id": None,
        "title": f"Dictionary validation {unique}",
    }


def _valid_data_json(db) -> dict[str, str | int]:
    org = db.scalar(select(AccountingOrganization).where(AccountingOrganization.code == "ORG-001"))
    counterparty = db.scalar(select(AccountingCounterparty).where(AccountingCounterparty.code == "CNT-001"))
    contract = db.scalar(
        select(AccountingCounterpartyContract).where(
            AccountingCounterpartyContract.organization_id == org.id,
            AccountingCounterpartyContract.counterparty_id == counterparty.id,
            AccountingCounterpartyContract.number == "142-П",
        )
    )
    currency = db.scalar(select(AccountingCurrency).where(AccountingCurrency.code == "KZT"))
    expense_item = db.scalar(select(AccountingExpenseItem).where(AccountingExpenseItem.code == "EXP-002"))
    operation_type = db.scalar(select(AccountingCashFlowOperationType).where(AccountingCashFlowOperationType.code == "supplier_payment"))
    project = db.scalar(select(AccountingProject).where(AccountingProject.code == "MAIN"))

    assert org is not None
    assert counterparty is not None
    assert contract is not None
    assert currency is not None
    assert expense_item is not None
    assert operation_type is not None
    assert project is not None

    return {
        "amount": 12345,
        "currency": "KZT",
        "paymentPurpose": "Dictionary validation test",
        "organization_id": str(org.id),
        "counterparty_id": str(counterparty.id),
        "contract_id": str(contract.id),
        "currency_id": str(currency.id),
        "cash_flow_operation_type_id": str(operation_type.id),
        "project_id": str(project.id),
        "expense_item_id": str(expense_item.id),
    }


def test_create_document_with_valid_dictionary_fields(client, db, users):
    document_type_id, document_type_version_id = _payment_request_version_with_management_accounting(db)
    payload = _base_payload(document_type_id, document_type_version_id, str(users["author"].id))
    payload["data_json"] = _valid_data_json(db)

    response = client.post("/api/v1/documents", json=payload, headers=auth_headers(str(users["author"].id)))

    assert response.status_code == 200, response.text
    data = response.json()["data_json"]
    assert data["contract_id"] == payload["data_json"]["contract_id"]
    assert data["organization_id"] == payload["data_json"]["organization_id"]
    assert data["counterparty_id"] == payload["data_json"]["counterparty_id"]


def test_rejects_unknown_dictionary_item(client, db, users):
    document_type_id, document_type_version_id = _payment_request_version_with_management_accounting(db)
    payload = _base_payload(document_type_id, document_type_version_id, str(users["author"].id))
    data_json = _valid_data_json(db)
    data_json["project_id"] = str(uuid4())
    payload["data_json"] = data_json

    response = client.post("/api/v1/documents", json=payload, headers=auth_headers(str(users["author"].id)))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "DOCUMENT_VALIDATION_ERROR"
    assert error["details"]["field"] == "project_id"


def test_rejects_contract_mismatch_with_org_and_counterparty(client, db, users):
    document_type_id, document_type_version_id = _payment_request_version_with_management_accounting(db)
    payload = _base_payload(document_type_id, document_type_version_id, str(users["author"].id))
    data_json = _valid_data_json(db)

    mismatched_contract = db.scalar(
        select(AccountingCounterpartyContract).where(AccountingCounterpartyContract.number == "55-R")
    )
    assert mismatched_contract is not None

    data_json["contract_id"] = str(mismatched_contract.id)
    payload["data_json"] = data_json

    response = client.post("/api/v1/documents", json=payload, headers=auth_headers(str(users["author"].id)))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "DOCUMENT_VALIDATION_ERROR"
    assert error["details"]["field"] == "contract_id"
    assert "Contract does not match" in error["details"]["reason"]
