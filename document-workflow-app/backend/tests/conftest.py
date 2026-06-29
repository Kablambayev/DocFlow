from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.accounting.models import (
    AccountingCashFlowOperationType,
    AccountingCounterparty,
    AccountingCounterpartyContract,
    AccountingCurrency,
    AccountingExpenseItem,
    AccountingOrganization,
    AccountingProject,
)
from app.main import app
from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.documents.models import Document
from app.modules.users.models import User
from app.modules.workflow.models import ApprovalRoute, ApprovalTask, TaskStatus
from scripts.seed_dev import main as seed_dev_main


@pytest.fixture(scope="session", autouse=True)
def seed_dev_data() -> None:
    seed_dev_main()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def auth_headers(user_id: str) -> dict[str, str]:
    return {"X-User-Id": user_id}


@pytest.fixture()
def users(db) -> dict[str, User]:
    result: dict[str, User] = {}
    for key, email in {
        "admin": "admin@example.com",
        "author": "author@example.com",
        "approver": "approver@example.com",
        "accounting_admin": "accounting_admin@example.com",
    }.items():
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None, f"Missing seed user {email}"
        result[key] = user
    return result


@pytest.fixture()
def seed_refs(db) -> dict[str, object]:
    document_type = db.scalar(select(DocumentType).where(DocumentType.code == "PaymentRequest"))
    assert document_type is not None

    document_type_version = db.scalar(
        select(DocumentTypeVersion).where(
            DocumentTypeVersion.document_type_id == document_type.id,
            DocumentTypeVersion.status == VersionStatus.PUBLISHED,
        )
    )
    assert document_type_version is not None

    route = db.scalar(select(ApprovalRoute).where(ApprovalRoute.document_type_id == document_type.id))
    assert route is not None

    organization = db.scalar(select(AccountingOrganization).where(AccountingOrganization.code == "ORG-001"))
    counterparty = db.scalar(select(AccountingCounterparty).where(AccountingCounterparty.code == "CNT-001"))
    contract = db.scalar(select(AccountingCounterpartyContract).where(AccountingCounterpartyContract.number == "142-П"))
    currency = db.scalar(select(AccountingCurrency).where(AccountingCurrency.code == "KZT"))
    cash_flow_operation_type = db.scalar(
        select(AccountingCashFlowOperationType).where(AccountingCashFlowOperationType.code == "supplier_payment")
    )
    project = db.scalar(select(AccountingProject).where(AccountingProject.code == "MAIN"))
    expense_item = db.scalar(select(AccountingExpenseItem).where(AccountingExpenseItem.code == "EXP-002"))

    assert organization is not None
    assert counterparty is not None
    assert contract is not None
    assert currency is not None
    assert cash_flow_operation_type is not None
    assert project is not None
    assert expense_item is not None

    return {
        "document_type": document_type,
        "document_type_version": document_type_version,
        "route": route,
        "accounting_data": {
            "organization_id": str(organization.id),
            "counterparty_id": str(counterparty.id),
            "contract_id": str(contract.id),
            "currency_id": str(currency.id),
            "cash_flow_operation_type_id": str(cash_flow_operation_type.id),
            "project_id": str(project.id),
            "expense_item_id": str(expense_item.id),
        },
    }


def document_payload(
    document_type_id: str,
    document_type_version_id: str,
    author_id: str,
    number: str | None = None,
    accounting_data: dict[str, str] | None = None,
) -> dict:
    unique = number or f"TEST-PAY-RBAC-{uuid4().hex[:12]}"
    dictionary_data = accounting_data or {}
    return {
        "document_type_id": document_type_id,
        "document_type_version_id": document_type_version_id,
        "number": unique,
        "document_date": datetime.now(timezone.utc).isoformat(),
        "author_id": author_id,
        "organization_id": None,
        "department_id": None,
        "title": f"RBAC regression {unique}",
        "data_json": {
            "amount": 1000,
            "currency": "KZT",
            "paymentPurpose": "RBAC regression test",
            "organization_id": dictionary_data.get("organization_id"),
            "counterparty_id": dictionary_data.get("counterparty_id"),
            "contract_id": dictionary_data.get("contract_id"),
            "currency_id": dictionary_data.get("currency_id"),
            "cash_flow_operation_type_id": dictionary_data.get("cash_flow_operation_type_id"),
            "project_id": dictionary_data.get("project_id"),
            "expense_item_id": dictionary_data.get("expense_item_id"),
        },
    }


def create_test_document(client: TestClient, actor_id: str, author_id: str, seed_refs: dict[str, object]) -> dict:
    payload = document_payload(
        str(seed_refs["document_type"].id),
        str(seed_refs["document_type_version"].id),
        author_id,
        accounting_data=seed_refs["accounting_data"],
    )
    response = client.post("/api/v1/documents", json=payload, headers=auth_headers(actor_id))
    assert response.status_code == 200, response.text
    return response.json()


def pending_task_for_document(db, document_id: str) -> ApprovalTask:
    task = db.scalar(
        select(ApprovalTask).where(
            ApprovalTask.document_id == document_id,
            ApprovalTask.status == TaskStatus.PENDING,
        )
    )
    assert task is not None, f"No pending task for document {document_id}"
    return task


def get_document(db, document_id: str) -> Document:
    document = db.get(Document, document_id)
    assert document is not None
    return document
