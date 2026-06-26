from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

# Allow running as: python scripts/seed_dev.py
ROOT_DIR = Path(__file__).resolve().parents[1]
import sys

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

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
    ("document_comment.read", "Read document comments"),
    ("document_comment.create", "Create document comments"),
    ("document_comment.update", "Update document comments"),
    ("document_comment.delete", "Delete document comments"),
    ("document_file.read", "Read document files"),
    ("document_file.upload", "Upload document files"),
    ("document_file.delete", "Delete document files"),
    ("notification.read", "Read notifications"),
    ("notification.update", "Update notifications"),
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
    ("accounting.read", "Read accounting dictionaries"),
    ("accounting.manage", "Manage accounting local dictionaries"),
    ("accounting.sync", "Sync accounting external dictionaries"),
]

ROLE_PERMISSIONS = {
    "admin": [code for code, _ in PERMISSIONS],
    "document_user": [
        "document.read",
        "document.create",
        "document.update",
        "document.submit",
        "document.withdraw",
        "document_comment.read",
        "document_comment.create",
        "document_comment.update",
        "document_comment.delete",
        "document_file.read",
        "document_file.upload",
        "document_file.delete",
        "notification.read",
        "notification.update",
        "document_type.read",
        "accounting.read",
    ],
    "approver": [
        "document.read",
        "document.approve",
        "document.reject",
        "document_comment.read",
        "document_comment.create",
        "document_file.read",
        "notification.read",
        "notification.update",
        "task.read",
        "accounting.read",
    ],
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
    "accounting_admin": [
        "accounting.read",
        "accounting.manage",
        "accounting.sync",
    ],
}

ROLE_NAMES = {
    "admin": "Administrator",
    "document_user": "Document user",
    "approver": "Approver",
    "document_constructor": "Document constructor",
    "workflow_admin": "Workflow administrator",
    "user_admin": "User administrator",
    "accounting_admin": "Accounting administrator",
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


def _find_or_create_by_external(db, model, external_id: str, name: str, *, code: str | None = None, extra: dict | None = None):
    existing = db.scalar(select(model).where(model.source_system == "1C", model.external_id == external_id))
    if existing is not None:
        existing.name = name
        if code is not None and hasattr(existing, "code"):
            existing.code = code
        if extra:
            for key, value in extra.items():
                setattr(existing, key, value)
        existing.is_active = True
        return existing

    payload = {
        "external_id": external_id,
        "code": code,
        "name": name,
        "is_active": True,
        "source_system": "1C",
        "raw_data": {},
    }
    if extra:
        payload.update(extra)
    item = model(**payload)
    db.add(item)
    db.flush()
    return item


def _find_or_create_local_by_code(db, model, code: str, name: str, extra: dict | None = None):
    existing = db.scalar(select(model).where(model.code == code))
    if existing is not None:
        existing.name = name
        existing.is_active = True
        if extra:
            for key, value in extra.items():
                setattr(existing, key, value)
        return existing

    payload = {"code": code, "name": name, "is_active": True}
    if extra:
        payload.update(extra)
    item = model(**payload)
    db.add(item)
    db.flush()
    return item


def seed_accounting_dictionaries(db) -> dict[str, object]:
    org_1 = _find_or_create_by_external(
        db,
        AccountingOrganization,
        "ORG-001",
        'ТОО "DocFlow Kazakhstan"',
        code="ORG-001",
        extra={"full_name": 'Товарищество с ограниченной ответственностью "DocFlow Kazakhstan"'},
    )
    org_2 = _find_or_create_by_external(
        db,
        AccountingOrganization,
        "ORG-002",
        'ТОО "Retail Group KZ"',
        code="ORG-002",
        extra={"full_name": 'Товарищество с ограниченной ответственностью "Retail Group KZ"'},
    )

    cnt_1 = _find_or_create_by_external(db, AccountingCounterparty, "CNT-001", 'ТОО "Alpha Supply"', code="CNT-001")
    cnt_2 = _find_or_create_by_external(db, AccountingCounterparty, "CNT-002", 'ТОО "Beta Services"', code="CNT-002")
    cnt_3 = _find_or_create_by_external(db, AccountingCounterparty, "CNT-003", 'ИП "Иванов"', code="CNT-003")

    cur_kzt = _find_or_create_by_external(
        db,
        AccountingCurrency,
        "CUR-KZT",
        "Тенге",
        code="KZT",
        extra={"full_name": "Казахстанский тенге", "numeric_code": "398"},
    )
    _find_or_create_by_external(
        db,
        AccountingCurrency,
        "CUR-USD",
        "Доллар США",
        code="USD",
        extra={"full_name": "Доллар США", "numeric_code": "840"},
    )
    _find_or_create_by_external(
        db,
        AccountingCurrency,
        "CUR-EUR",
        "Евро",
        code="EUR",
        extra={"full_name": "Евро", "numeric_code": "978"},
    )

    _find_or_create_by_external(db, AccountingExpenseItem, "EXP-001", "Аренда", code="EXP-001")
    _find_or_create_by_external(db, AccountingExpenseItem, "EXP-002", "IT-услуги", code="EXP-002")
    _find_or_create_by_external(db, AccountingExpenseItem, "EXP-003", "Сырье и материалы", code="EXP-003")
    _find_or_create_by_external(db, AccountingExpenseItem, "EXP-004", "Маркетинг", code="EXP-004")
    _find_or_create_by_external(db, AccountingExpenseItem, "EXP-005", "Прочие расходы", code="EXP-005")

    contract_seed = [
        ("CTR-ORG1-CNT1-142", org_1.id, cnt_1.id, cur_kzt.id, "142-П", "Договор поставки №142-П"),
        ("CTR-ORG1-CNT1-18", org_1.id, cnt_1.id, cur_kzt.id, "18-У", "Договор услуг №18-У"),
        ("CTR-ORG1-CNT2-77", org_1.id, cnt_2.id, cur_kzt.id, "77-IT", "Договор IT-услуг №77-IT"),
        ("CTR-ORG2-CNT1-55", org_2.id, cnt_1.id, cur_kzt.id, "55-R", "Договор поставки Retail №55-R"),
        ("CTR-ORG2-CNT3-11", org_2.id, cnt_3.id, cur_kzt.id, "11-А", "Договор аренды №11-А"),
    ]
    contracts: list[AccountingCounterpartyContract] = []
    for external_id, organization_id, counterparty_id, currency_id, number, name in contract_seed:
        existing = db.scalar(
            select(AccountingCounterpartyContract).where(
                AccountingCounterpartyContract.source_system == "1C",
                AccountingCounterpartyContract.external_id == external_id,
            )
        )
        if existing is None:
            existing = AccountingCounterpartyContract(
                external_id=external_id,
                organization_id=organization_id,
                counterparty_id=counterparty_id,
                currency_id=currency_id,
                code=number,
                name=name,
                number=number,
                contract_date=datetime.now(timezone.utc).date(),
                is_active=True,
                source_system="1C",
                raw_data={},
            )
            db.add(existing)
            db.flush()
        else:
            existing.organization_id = organization_id
            existing.counterparty_id = counterparty_id
            existing.currency_id = currency_id
            existing.code = number
            existing.name = name
            existing.number = number
            existing.is_active = True
        contracts.append(existing)

    _find_or_create_local_by_code(db, AccountingCashFlowOperationType, "supplier_payment", "Оплата поставщику", {"description": None, "sort_order": 10})
    _find_or_create_local_by_code(db, AccountingCashFlowOperationType, "tax_payment", "Оплата налогов", {"description": None, "sort_order": 20})
    _find_or_create_local_by_code(db, AccountingCashFlowOperationType, "salary_payment", "Выплата зарплаты", {"description": None, "sort_order": 30})
    _find_or_create_local_by_code(db, AccountingCashFlowOperationType, "loan_payment", "Погашение займа", {"description": None, "sort_order": 40})
    _find_or_create_local_by_code(db, AccountingCashFlowOperationType, "other_payment", "Прочий платеж", {"description": None, "sort_order": 100})

    _find_or_create_local_by_code(db, AccountingProject, "MAIN", "Основная деятельность")
    _find_or_create_local_by_code(db, AccountingProject, "ERP", "Внедрение ERP")
    _find_or_create_local_by_code(db, AccountingProject, "WAREHOUSE", "Складской проект")
    _find_or_create_local_by_code(db, AccountingProject, "RETAIL", "Розничная сеть")

    return {
        "organization": org_1,
        "counterparty": cnt_1,
        "contract": contracts[0],
        "currency": cur_kzt,
        "expense_item": db.scalar(select(AccountingExpenseItem).where(AccountingExpenseItem.code == "EXP-002")),
        "cash_flow_operation_type": db.scalar(
            select(AccountingCashFlowOperationType).where(AccountingCashFlowOperationType.code == "supplier_payment")
        ),
        "project": db.scalar(select(AccountingProject).where(AccountingProject.code == "MAIN")),
    }


def enrich_payment_request_schema(schema_json: dict | None) -> dict:
    schema = deepcopy(schema_json) if isinstance(schema_json, dict) else {"sections": []}
    if not isinstance(schema.get("sections"), list):
        schema["sections"] = []
    sections = schema["sections"]

    main_section = next((section for section in sections if section.get("code") == "main"), None)
    if main_section is None:
        main_section = {"code": "main", "name": "Основные данные", "fields": []}
        sections.append(main_section)
    if not isinstance(main_section.get("fields"), list):
        main_section["fields"] = []

    main_fields = {field.get("code"): field for field in main_section["fields"] if isinstance(field, dict)}
    main_fields.setdefault("amount", {"code": "amount", "name": "Сумма", "type": "money", "required": True})
    main_fields.setdefault("currency", {"code": "currency", "name": "Валюта", "type": "string", "required": True})
    main_fields.setdefault("paymentPurpose", {"code": "paymentPurpose", "name": "Назначение платежа", "type": "text", "required": True})
    main_section["fields"] = list(main_fields.values())

    accounting_fields = [
        {
            "code": "organization_id",
            "name": "Организация",
            "type": "dictionary",
            "required": True,
            "settings": {"dictionary": "organizations", "valueField": "id", "labelField": "name", "searchable": True},
        },
        {
            "code": "counterparty_id",
            "name": "Контрагент",
            "type": "dictionary",
            "required": True,
            "settings": {"dictionary": "counterparties", "valueField": "id", "labelField": "name", "searchable": True},
        },
        {
            "code": "contract_id",
            "name": "Договор контрагента",
            "type": "dictionary",
            "required": True,
            "settings": {
                "dictionary": "counterparty_contracts",
                "valueField": "id",
                "labelField": "name",
                "searchable": True,
                "dependsOn": [
                    {"field": "organization_id", "param": "organization_id"},
                    {"field": "counterparty_id", "param": "counterparty_id"},
                ],
            },
        },
        {
            "code": "currency_id",
            "name": "Валюта",
            "type": "dictionary",
            "required": True,
            "settings": {"dictionary": "currencies", "valueField": "id", "labelField": "code", "searchable": True},
        },
        {
            "code": "cash_flow_operation_type_id",
            "name": "Вид операции денежных средств",
            "type": "dictionary",
            "required": True,
            "settings": {
                "dictionary": "cash_flow_operation_types",
                "valueField": "id",
                "labelField": "name",
                "searchable": True,
            },
        },
        {
            "code": "project_id",
            "name": "Проект",
            "type": "dictionary",
            "required": True,
            "settings": {"dictionary": "projects", "valueField": "id", "labelField": "name", "searchable": True},
        },
        {
            "code": "expense_item_id",
            "name": "Статья затрат",
            "type": "dictionary",
            "required": True,
            "settings": {"dictionary": "expense_items", "valueField": "id", "labelField": "name", "searchable": True},
        },
    ]

    accounting_section = next((section for section in sections if section.get("code") == "management_accounting"), None)
    if accounting_section is None:
        accounting_section = {"code": "management_accounting", "name": "Управленческий учет", "fields": []}
        sections.append(accounting_section)
    if not isinstance(accounting_section.get("fields"), list):
        accounting_section["fields"] = []

    accounting_field_map = {
        field.get("code"): field for field in accounting_section["fields"] if isinstance(field, dict)
    }
    for field in accounting_fields:
        accounting_field_map[field["code"]] = field
    accounting_section["fields"] = list(accounting_field_map.values())

    return schema


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
    existing_published_versions = list(
        db.scalars(
            select(DocumentTypeVersion)
            .where(
                DocumentTypeVersion.document_type_id == document_type_id,
                DocumentTypeVersion.status == VersionStatus.PUBLISHED,
            )
            .order_by(DocumentTypeVersion.version_number.desc())
        )
    )
    if existing_published_versions:
        for published_version in existing_published_versions:
            published_version.schema_json = enrich_payment_request_schema(published_version.schema_json)
        db.flush()
        return existing_published_versions[0]

    max_version = db.scalar(
        select(DocumentTypeVersion.version_number)
        .where(DocumentTypeVersion.document_type_id == document_type_id)
        .order_by(DocumentTypeVersion.version_number.desc())
        .limit(1)
    )
    next_version = (max_version or 0) + 1

    schema_json = enrich_payment_request_schema(None)

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


def get_or_create_draft_document(db, document_type_id, doc_type_version_id, author_id, accounting_refs: dict[str, object]) -> Document:
    number = "PAY-000001"
    existing = db.scalar(select(Document).where(Document.number == number))
    if existing is not None:
        existing.data_json = {
            **(existing.data_json or {}),
            "organization_id": str(accounting_refs["organization"].id),
            "counterparty_id": str(accounting_refs["counterparty"].id),
            "contract_id": str(accounting_refs["contract"].id),
            "currency_id": str(accounting_refs["currency"].id),
            "cash_flow_operation_type_id": str(accounting_refs["cash_flow_operation_type"].id),
            "project_id": str(accounting_refs["project"].id),
            "expense_item_id": str(accounting_refs["expense_item"].id),
        }
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
        data_json={
            "amount": 1500000,
            "currency": "KZT",
            "paymentPurpose": "Оплата по договору",
            "organization_id": str(accounting_refs["organization"].id),
            "counterparty_id": str(accounting_refs["counterparty"].id),
            "contract_id": str(accounting_refs["contract"].id),
            "currency_id": str(accounting_refs["currency"].id),
            "cash_flow_operation_type_id": str(accounting_refs["cash_flow_operation_type"].id),
            "project_id": str(accounting_refs["project"].id),
            "expense_item_id": str(accounting_refs["expense_item"].id),
        },
    )
    db.add(doc)
    db.flush()
    return doc


def main() -> None:
    db = SessionLocal()
    try:
        roles = seed_permissions_and_roles(db)
        accounting_refs = seed_accounting_dictionaries(db)

        admin = get_or_create_user(db, "admin@example.com", "Admin User")
        author = get_or_create_user(db, "author@example.com", "Author User")
        approver = get_or_create_user(db, "approver@example.com", "Approver User")
        accounting_admin = get_or_create_user(db, "accounting_admin@example.com", "Accounting Admin")

        assign_role(admin, roles["admin"])
        assign_role(author, roles["document_user"])
        assign_role(approver, roles["approver"])
        assign_role(accounting_admin, roles["accounting_admin"])

        doc_type = get_or_create_document_type(db)
        doc_type_version = get_or_create_published_doc_type_version(db, doc_type.id)

        route = get_or_create_route(db, doc_type.id)
        _route_version = get_or_create_published_route_version(db, route.id, approver.id)

        _matrix_rule = get_or_create_matrix_rule(db, doc_type.id, route.id)
        document = get_or_create_draft_document(db, doc_type.id, doc_type_version.id, author.id, accounting_refs)

        db.commit()

        print("Seed completed")
        print(f"admin_id={admin.id}")
        print(f"author_id={author.id}")
        print(f"approver_id={approver.id}")
        print(f"accounting_admin_id={accounting_admin.id}")
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
