from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

# Allow running as: python scripts/seed_dev.py
ROOT_DIR = Path(__file__).resolve().parents[1]
import sys

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.db.session import SessionLocal
from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.documents.models import Document, DocumentApprovalStatus
from app.modules.roles.models import Role
from app.modules.users.models import Permission, User
from app.modules.workflow.models import ApprovalMatrixRule, ApprovalRoute, ApprovalRouteVersion


def get_or_create_user(db, email: str, full_name: str) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        return existing

    user = User(email=email, full_name=full_name, is_active=True)
    db.add(user)
    db.flush()
    return user


PERMISSIONS = [
    ("admin.access", "Admin access"),
    ("document.read", "Read documents"),
    ("document.create", "Create documents"),
    ("document.update", "Update documents"),
    ("document.submit", "Submit documents"),
    ("document.withdraw", "Withdraw documents"),
    ("document.approve", "Approve documents"),
    ("document.reject", "Reject documents"),
    ("document_file.read", "Read document files"),
    ("document_file.upload", "Upload document files"),
    ("document_file.delete", "Delete document files"),
    ("document_type.read", "Read document types"),
    ("document_type.create", "Create document types"),
    ("document_type.update", "Update document types"),
    ("document_type.publish", "Publish document types"),
    ("approval_route.read", "Read approval routes"),
    ("approval_route.create", "Create approval routes"),
    ("approval_route.update", "Update approval routes"),
    ("approval_route.publish", "Publish approval routes"),
    ("approval_matrix.read", "Read approval matrix"),
    ("approval_matrix.create", "Create approval matrix"),
    ("approval_matrix.update", "Update approval matrix"),
    ("approval_matrix.delete", "Delete approval matrix"),
    ("user.read", "Read users"),
    ("user.create", "Create users"),
    ("user.update", "Update users"),
    ("role.read", "Read roles"),
    ("role.create", "Create roles"),
    ("role.update", "Update roles"),
    ("permission.read", "Read permissions"),
    ("task.read", "Read tasks"),
    ("audit.read", "Read audit"),
]

ROLE_PERMISSIONS = {
    "admin": [code for code, _ in PERMISSIONS],
    "document_user": [
        "document.read",
        "document.create",
        "document.update",
        "document.submit",
        "document.withdraw",
        "document_file.read",
        "document_file.upload",
        "document_file.delete",
        "document_type.read",
    ],
    "approver": ["document.read", "document.approve", "document.reject", "document_file.read", "task.read"],
    "document_constructor": [
        "document_type.read",
        "document_type.create",
        "document_type.update",
        "document_type.publish",
    ],
    "workflow_admin": [
        "approval_route.read",
        "approval_route.create",
        "approval_route.update",
        "approval_route.publish",
        "approval_matrix.read",
        "approval_matrix.create",
        "approval_matrix.update",
        "approval_matrix.delete",
        "document_type.read",
    ],
    "user_admin": [
        "user.read",
        "user.create",
        "user.update",
        "role.read",
        "role.create",
        "role.update",
        "permission.read",
    ],
}

ROLE_NAMES = {
    "admin": "Administrator",
    "document_user": "Document user",
    "approver": "Approver",
    "document_constructor": "Document constructor",
    "workflow_admin": "Workflow administrator",
    "user_admin": "User administrator",
}


def seed_permissions_and_roles(db) -> dict[str, Role]:
    permissions_by_code: dict[str, Permission] = {}
    for code, name in PERMISSIONS:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, name=name, description=None)
            db.add(permission)
            db.flush()
        permissions_by_code[code] = permission

    roles_by_code: dict[str, Role] = {}
    for code, permission_codes in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.code == code))
        if role is None:
            role = Role(code=code, name=ROLE_NAMES[code], description=None, is_active=True)
            db.add(role)
            db.flush()
        role.is_active = True
        for permission_code in permission_codes:
            permission = permissions_by_code[permission_code]
            if permission not in role.permissions:
                role.permissions.append(permission)
        roles_by_code[code] = role

    return roles_by_code


def assign_role(user: User, role: Role) -> None:
    if role not in user.roles:
        user.roles.append(role)


def get_or_create_document_type(db) -> DocumentType:
    code = "PaymentRequest"
    existing = db.scalar(select(DocumentType).where(DocumentType.code == code))
    if existing is not None:
        return existing

    item = DocumentType(
        code=code,
        name="Заявка на оплату",
        description="Документ для заявки на оплату",
        is_system=True,
        is_active=True,
    )
    db.add(item)
    db.flush()
    return item


def get_or_create_published_doc_type_version(db, document_type_id) -> DocumentTypeVersion:
    existing_published = db.scalar(
        select(DocumentTypeVersion).where(
            DocumentTypeVersion.document_type_id == document_type_id,
            DocumentTypeVersion.status == VersionStatus.PUBLISHED,
        )
    )
    if existing_published is not None:
        return existing_published

    max_version = db.scalar(
        select(DocumentTypeVersion.version_number)
        .where(DocumentTypeVersion.document_type_id == document_type_id)
        .order_by(DocumentTypeVersion.version_number.desc())
        .limit(1)
    )
    next_version = (max_version or 0) + 1

    schema_json = {
        "sections": [
            {
                "code": "main",
                "name": "Основные данные",
                "fields": [
                    {"code": "amount", "name": "Сумма", "type": "money", "required": True},
                    {"code": "currency", "name": "Валюта", "type": "string", "required": True},
                    {"code": "paymentPurpose", "name": "Назначение платежа", "type": "text", "required": True},
                ],
            }
        ]
    }

    version = DocumentTypeVersion(
        document_type_id=document_type_id,
        version_number=next_version,
        status=VersionStatus.PUBLISHED,
        schema_json=schema_json,
        published_at=datetime.now(timezone.utc),
    )
    db.add(version)
    db.flush()
    return version


def get_or_create_route(db, document_type_id) -> ApprovalRoute:
    code = "payment_request_default"
    existing = db.scalar(
        select(ApprovalRoute).where(
            ApprovalRoute.document_type_id == document_type_id,
            ApprovalRoute.code == code,
        )
    )
    if existing is not None:
        return existing

    route = ApprovalRoute(
        document_type_id=document_type_id,
        code=code,
        name="Базовый маршрут заявки на оплату",
        description="Один согласующий",
        is_active=True,
    )
    db.add(route)
    db.flush()
    return route


def get_or_create_published_route_version(db, route_id, approver_id) -> ApprovalRouteVersion:
    existing = db.scalar(
        select(ApprovalRouteVersion).where(
            ApprovalRouteVersion.route_id == route_id,
            ApprovalRouteVersion.status == "published",
        )
    )
    if existing is not None:
        return existing

    max_version = db.scalar(
        select(ApprovalRouteVersion.version_number)
        .where(ApprovalRouteVersion.route_id == route_id)
        .order_by(ApprovalRouteVersion.version_number.desc())
        .limit(1)
    )
    next_version = (max_version or 0) + 1

    route_schema_json = {
        "steps": [
            {
                "order": 1,
                "name": "Первый согласующий",
                "type": "sequential",
                "approverResolver": {"type": "specific_user", "userId": str(approver_id)},
                "decisionPolicy": "all",
                "slaHours": 24,
            }
        ]
    }

    version = ApprovalRouteVersion(
        route_id=route_id,
        version_number=next_version,
        status="published",
        route_schema_json=route_schema_json,
        published_at=datetime.now(timezone.utc),
    )
    db.add(version)
    db.flush()
    return version


def get_or_create_matrix_rule(db, document_type_id, route_id) -> ApprovalMatrixRule:
    name = "Все заявки на оплату"
    existing = db.scalar(
        select(ApprovalMatrixRule).where(
            ApprovalMatrixRule.document_type_id == document_type_id,
            ApprovalMatrixRule.name == name,
        )
    )
    if existing is not None:
        if not existing.is_active:
            existing.is_active = True
        return existing

    rule = ApprovalMatrixRule(
        document_type_id=document_type_id,
        priority=1,
        name=name,
        condition_json={"operator": "and", "conditions": []},
        route_id=route_id,
        is_active=True,
    )
    db.add(rule)
    db.flush()
    return rule


def get_or_create_draft_document(db, document_type_id, doc_type_version_id, author_id) -> Document:
    number = "PAY-000001"
    existing = db.scalar(select(Document).where(Document.number == number))
    if existing is not None:
        return existing

    doc = Document(
        document_type_id=document_type_id,
        document_type_version_id=doc_type_version_id,
        number=number,
        document_date=datetime.now(timezone.utc),
        author_id=author_id,
        organization_id=None,
        department_id=None,
        approval_status=DocumentApprovalStatus.DRAFT,
        business_status=None,
        title="Заявка на оплату PAY-000001",
        data_json={"amount": 1500000, "currency": "KZT", "paymentPurpose": "Оплата по договору"},
    )
    db.add(doc)
    db.flush()
    return doc


def main() -> None:
    db = SessionLocal()
    try:
        roles = seed_permissions_and_roles(db)
        admin = get_or_create_user(db, "admin@example.com", "Admin User")
        author = get_or_create_user(db, "author@example.com", "Author User")
        approver = get_or_create_user(db, "approver@example.com", "Approver User")
        assign_role(admin, roles["admin"])
        assign_role(author, roles["document_user"])
        assign_role(approver, roles["approver"])

        doc_type = get_or_create_document_type(db)
        doc_type_version = get_or_create_published_doc_type_version(db, doc_type.id)

        route = get_or_create_route(db, doc_type.id)
        _route_version = get_or_create_published_route_version(db, route.id, approver.id)

        _matrix_rule = get_or_create_matrix_rule(db, doc_type.id, route.id)
        document = get_or_create_draft_document(db, doc_type.id, doc_type_version.id, author.id)

        db.commit()

        print("Seed completed")
        print(f"admin_id={admin.id}")
        print(f"author_id={author.id}")
        print(f"approver_id={approver.id}")
        print(f"document_type_id={doc_type.id}")
        print(f"document_type_version_id={doc_type_version.id}")
        print(f"route_id={route.id}")
        print(f"document_id={document.id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
