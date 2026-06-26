from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
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

    return {"document_type": document_type, "document_type_version": document_type_version, "route": route}


def document_payload(document_type_id: str, document_type_version_id: str, author_id: str, number: str | None = None) -> dict:
    unique = number or f"TEST-PAY-RBAC-{uuid4().hex[:12]}"
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
        },
    }


def create_test_document(client: TestClient, actor_id: str, author_id: str, seed_refs: dict[str, object]) -> dict:
    payload = document_payload(
        str(seed_refs["document_type"].id),
        str(seed_refs["document_type_version"].id),
        author_id,
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
