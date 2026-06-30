from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.modules.accounting.models import (
    AccountingCashFlowItem,
    AccountingCashFlowOperationType,
    AccountingCurrency,
    AccountingOrganization,
    AccountingProject,
)
from app.modules.document_types.models import DocumentType, DocumentTypeVersion, VersionStatus
from app.modules.documents.models import Document, DocumentApprovalStatus
from app.modules.users.models import User
from tests.conftest import auth_headers


def _headers_for_email(db, email: str) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return auth_headers(str(user.id))


def _report_params(**overrides) -> dict:
    params = {"date_from": "2030-01-01", "date_to": "2030-12-31"}
    params.update(overrides)
    return params


def _unique_year(base: int = 2030) -> int:
    return base + (uuid4().int % 200)


def _report_refs(db) -> dict[str, object]:
    document_type = db.scalar(select(DocumentType).where(DocumentType.code == "CashFlowAllocation"))
    assert document_type is not None
    version = db.scalar(
        select(DocumentTypeVersion).where(
            DocumentTypeVersion.document_type_id == document_type.id,
            DocumentTypeVersion.status == VersionStatus.PUBLISHED,
        )
    )
    assert version is not None
    author = db.scalar(select(User).where(User.email == "accounting_admin@example.com"))
    org1 = db.scalar(select(AccountingOrganization).where(AccountingOrganization.code == "ORG-001"))
    org2 = db.scalar(select(AccountingOrganization).where(AccountingOrganization.code == "ORG-002"))
    project_main = db.scalar(select(AccountingProject).where(AccountingProject.code == "MAIN"))
    project_erp = db.scalar(select(AccountingProject).where(AccountingProject.code == "ERP"))
    item_inflow = db.scalar(select(AccountingCashFlowItem).where(AccountingCashFlowItem.code == "DDS-002"))
    item_outflow = db.scalar(select(AccountingCashFlowItem).where(AccountingCashFlowItem.code == "DDS-001"))
    currency_kzt = db.scalar(select(AccountingCurrency).where(AccountingCurrency.code == "KZT"))
    currency_usd = db.scalar(select(AccountingCurrency).where(AccountingCurrency.code == "USD"))
    operation_type = db.scalar(select(AccountingCashFlowOperationType).where(AccountingCashFlowOperationType.code == "supplier_payment"))
    assert all([author, org1, org2, project_main, project_erp, item_inflow, item_outflow, currency_kzt, currency_usd, operation_type])
    return {
        "document_type": document_type,
        "version": version,
        "author": author,
        "org1": org1,
        "org2": org2,
        "project_main": project_main,
        "project_erp": project_erp,
        "item_inflow": item_inflow,
        "item_outflow": item_outflow,
        "currency_kzt": currency_kzt,
        "currency_usd": currency_usd,
        "operation_type": operation_type,
    }


def _create_allocation(
    db,
    refs: dict[str, object],
    *,
    source_number: str,
    source_date: str | None,
    allocation_status: str = "Completed",
    direction: str | None = "Inflow",
    amount=100,
    organization_id=None,
    project_id=None,
    cash_flow_item_id=None,
    cash_flow_operation_type_id=None,
    currency_id=None,
    source_changed: bool = False,
):
    document = Document(
        document_type_id=refs["document_type"].id,
        document_type_version_id=refs["version"].id,
        number=f"CFA-TEST-{uuid4().hex[:10]}",
        document_date=datetime.now(timezone.utc),
        author_id=refs["author"].id,
        organization_id=None,
        department_id=None,
        approval_status=DocumentApprovalStatus.DRAFT,
        business_status=None,
        title=f"BDDS report test {source_number}",
        data_json={
            "source_system": "1C",
            "source_document_external_id": f"bdds-{uuid4().hex[:12]}",
            "source_document_number": source_number,
            "source_document_type_1c": "ТестовыйДокумент1С",
            "source_document_date": source_date,
            "cash_flow_direction": direction,
            "organization_id": str(organization_id) if organization_id else None,
            "project_id": str(project_id) if project_id else None,
            "cash_flow_item_id": str(cash_flow_item_id) if cash_flow_item_id else None,
            "cash_flow_operation_type_id": str(cash_flow_operation_type_id) if cash_flow_operation_type_id else None,
            "currency_id": str(currency_id) if currency_id else None,
            "amount": amount,
            "allocation_status": allocation_status,
            "source_changed": source_changed,
        },
    )
    db.add(document)
    db.flush()
    return document


def test_bdds_report_permissions(client, db, users):
    params = _report_params()
    no_auth = client.get("/api/v1/cash-flow/bdds-report/summary", params=params)
    assert no_auth.status_code == 401

    no_permission = client.get("/api/v1/cash-flow/bdds-report/summary", params=params, headers=auth_headers(str(users["author"].id)))
    assert no_permission.status_code == 403

    accounting_admin = client.get(
        "/api/v1/cash-flow/bdds-report/summary",
        params=params,
        headers=_headers_for_email(db, "accounting_admin@example.com"),
    )
    assert accounting_admin.status_code == 200, accounting_admin.text

    admin = client.get("/api/v1/cash-flow/bdds-report/summary", params=params, headers=auth_headers(str(users["admin"].id)))
    assert admin.status_code == 200, admin.text


def test_bdds_report_validation(client, db):
    headers = _headers_for_email(db, "accounting_admin@example.com")

    missing_from = client.get("/api/v1/cash-flow/bdds-report/summary", params={"date_to": "2030-01-31"}, headers=headers)
    assert missing_from.status_code == 422

    missing_to = client.get("/api/v1/cash-flow/bdds-report/summary", params={"date_from": "2030-01-01"}, headers=headers)
    assert missing_to.status_code == 422

    invalid_period = client.get(
        "/api/v1/cash-flow/bdds-report/summary",
        params={"date_from": "2030-02-01", "date_to": "2030-01-01"},
        headers=headers,
    )
    assert invalid_period.status_code == 422
    assert invalid_period.json()["error"]["code"] == "BDDS_REPORT_INVALID_PERIOD"

    too_long = client.get(
        "/api/v1/cash-flow/bdds-report/summary",
        params={"date_from": "2030-01-01", "date_to": "2035-01-02"},
        headers=headers,
    )
    assert too_long.status_code == 422
    assert too_long.json()["error"]["code"] == "BDDS_REPORT_PERIOD_TOO_LONG"

    invalid_group_period = client.get(
        "/api/v1/cash-flow/bdds-report/by-periods",
        params={"date_from": "2030-01-01", "date_to": "2030-12-31", "group_period": "bad"},
        headers=headers,
    )
    assert invalid_group_period.status_code == 422
    assert invalid_group_period.json()["error"]["code"] == "BDDS_REPORT_INVALID_GROUP_PERIOD"


def test_bdds_report_summary_groupings_and_filters(client, db):
    refs = _report_refs(db)
    year = _unique_year(2030)

    _create_allocation(
        db,
        refs,
        source_number="SUM-KZT-INFLOW",
        source_date=f"{year}-01-10",
        direction="Inflow",
        amount=1000,
        organization_id=refs["org1"].id,
        project_id=refs["project_main"].id,
        cash_flow_item_id=refs["item_inflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=refs["currency_kzt"].id,
    )
    _create_allocation(
        db,
        refs,
        source_number="SUM-KZT-OUTFLOW",
        source_date=f"{year}-01-11",
        direction="Outflow",
        amount=400,
        organization_id=refs["org1"].id,
        project_id=refs["project_main"].id,
        cash_flow_item_id=refs["item_outflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=refs["currency_kzt"].id,
    )
    _create_allocation(
        db,
        refs,
        source_number="SUM-USD-INFLOW",
        source_date=f"{year}-02-12",
        direction="Inflow",
        amount=50,
        organization_id=refs["org2"].id,
        project_id=refs["project_erp"].id,
        cash_flow_item_id=refs["item_inflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=refs["currency_usd"].id,
    )
    _create_allocation(
        db,
        refs,
        source_number="SUM-NO-PROJECT",
        source_date=f"{year}-03-01",
        direction="Outflow",
        amount=70,
        organization_id=refs["org1"].id,
        project_id=None,
        cash_flow_item_id=refs["item_outflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=refs["currency_kzt"].id,
    )
    _create_allocation(
        db,
        refs,
        source_number="SUM-NEEDS",
        source_date=f"{year}-04-01",
        allocation_status="NeedsEnrichment",
        direction="Outflow",
        amount=300,
        organization_id=refs["org1"].id,
        project_id=refs["project_main"].id,
        cash_flow_item_id=refs["item_outflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=refs["currency_kzt"].id,
    )
    _create_allocation(
        db,
        refs,
        source_number="SUM-IGNORED",
        source_date=f"{year}-04-02",
        allocation_status="Ignored",
        direction="Inflow",
        amount=500,
        organization_id=refs["org1"].id,
        project_id=refs["project_main"].id,
        cash_flow_item_id=refs["item_inflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=refs["currency_kzt"].id,
    )
    _create_allocation(
        db,
        refs,
        source_number="SUM-DRAFT",
        source_date=f"{year}-04-03",
        allocation_status="Draft",
        direction="Inflow",
        amount=200,
        organization_id=refs["org1"].id,
        project_id=refs["project_main"].id,
        cash_flow_item_id=refs["item_inflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=refs["currency_kzt"].id,
    )
    _create_allocation(
        db,
        refs,
        source_number="SUM-MISSING-CURRENCY",
        source_date=f"{year}-04-04",
        allocation_status="Completed",
        direction="Inflow",
        amount=150,
        organization_id=refs["org1"].id,
        project_id=refs["project_main"].id,
        cash_flow_item_id=refs["item_inflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=None,
    )
    _create_allocation(
        db,
        refs,
        source_number="SUM-ZERO-AMOUNT",
        source_date=f"{year}-04-05",
        allocation_status="Completed",
        direction="Inflow",
        amount=0,
        organization_id=refs["org1"].id,
        project_id=refs["project_main"].id,
        cash_flow_item_id=refs["item_inflow"].id,
        cash_flow_operation_type_id=refs["operation_type"].id,
        currency_id=refs["currency_kzt"].id,
    )
    db.commit()

    headers = _headers_for_email(db, "accounting_admin@example.com")

    summary = client.get(
        "/api/v1/cash-flow/bdds-report/summary",
        params={"date_from": f"{year}-01-01", "date_to": f"{year}-12-31"},
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    summary_body = summary.json()
    assert summary_body["currency"] is None
    assert summary_body["inflow_total"] is None
    assert summary_body["outflow_total"] is None
    assert summary_body["net_cash_flow"] is None
    assert summary_body["allocations_count"] == 4
    assert summary_body["inflow_count"] == 2
    assert summary_body["outflow_count"] == 2
    assert summary_body["diagnostics"] == {
        "ignored_allocations_count": 1,
        "invalid_allocations_count": 2,
        "needs_enrichment_count": 1,
    }
    totals_by_currency = {item["currency"]["code"]: item for item in summary_body["totals_by_currency"]}
    assert totals_by_currency["KZT"]["inflow_total"] == "1000"
    assert totals_by_currency["KZT"]["outflow_total"] == "470"
    assert totals_by_currency["KZT"]["net_cash_flow"] == "530"
    assert totals_by_currency["USD"]["inflow_total"] == "50"
    assert totals_by_currency["USD"]["outflow_total"] == "0"

    summary_kzt = client.get(
        "/api/v1/cash-flow/bdds-report/summary",
        params={"date_from": f"{year}-01-01", "date_to": f"{year}-12-31", "currency_id": str(refs["currency_kzt"].id)},
        headers=headers,
    )
    assert summary_kzt.status_code == 200, summary_kzt.text
    summary_kzt_body = summary_kzt.json()
    assert summary_kzt_body["currency"]["code"] == "KZT"
    assert summary_kzt_body["inflow_total"] == "1000"
    assert summary_kzt_body["outflow_total"] == "470"
    assert summary_kzt_body["net_cash_flow"] == "530"

    by_items = client.get(
        "/api/v1/cash-flow/bdds-report/by-items",
        params={"date_from": f"{year}-01-01", "date_to": f"{year}-12-31"},
        headers=headers,
    )
    assert by_items.status_code == 200, by_items.text
    items_body = by_items.json()
    assert items_body["total"] == 3
    assert any(item["cash_flow_item"]["code"] == "DDS-001" and item["outflow_total"] == "470" for item in items_body["items"])
    assert any(item["cash_flow_item"]["code"] == "DDS-002" and item["currency"]["code"] == "USD" for item in items_body["items"])

    by_projects = client.get(
        "/api/v1/cash-flow/bdds-report/by-projects",
        params={"date_from": f"{year}-01-01", "date_to": f"{year}-12-31"},
        headers=headers,
    )
    assert by_projects.status_code == 200, by_projects.text
    projects_body = by_projects.json()
    assert any(item["project"] is None and item["project_name"] == "Без проекта" and item["outflow_total"] == "70" for item in projects_body["items"])

    by_orgs = client.get(
        "/api/v1/cash-flow/bdds-report/by-organizations",
        params={"date_from": f"{year}-01-01", "date_to": f"{year}-12-31"},
        headers=headers,
    )
    assert by_orgs.status_code == 200, by_orgs.text
    orgs_body = by_orgs.json()
    assert any(item["organization"]["code"] == "ORG-001" and item["currency"]["code"] == "KZT" for item in orgs_body["items"])
    assert any(item["organization"]["code"] == "ORG-002" and item["currency"]["code"] == "USD" for item in orgs_body["items"])

    filtered = client.get(
        "/api/v1/cash-flow/bdds-report/summary",
        params={
            "organization_id": str(refs["org2"].id),
            "project_id": str(refs["project_erp"].id),
            "cash_flow_item_id": str(refs["item_inflow"].id),
            "cash_flow_operation_type_id": str(refs["operation_type"].id),
            "currency_id": str(refs["currency_usd"].id),
            "date_from": f"{year}-02-01",
            "date_to": f"{year}-02-28",
        },
        headers=headers,
    )
    assert filtered.status_code == 200, filtered.text
    filtered_body = filtered.json()
    assert filtered_body["inflow_total"] == "50"
    assert filtered_body["outflow_total"] == "0"
    assert filtered_body["net_cash_flow"] == "50"


def test_bdds_report_by_periods(client, db):
    refs = _report_refs(db)
    year = _unique_year(2050)
    for source_number, source_date, direction, amount in [
        ("PER-1", f"{year}-01-02", "Inflow", 100),
        ("PER-2", f"{year}-01-03", "Outflow", 40),
        ("PER-3", f"{year}-02-15", "Inflow", 60),
        ("PER-4", f"{year}-04-10", "Inflow", 30),
    ]:
        _create_allocation(
            db,
            refs,
            source_number=source_number,
            source_date=source_date,
            direction=direction,
            amount=amount,
            organization_id=refs["org1"].id,
            project_id=refs["project_main"].id,
            cash_flow_item_id=refs["item_inflow"].id if direction == "Inflow" else refs["item_outflow"].id,
            cash_flow_operation_type_id=refs["operation_type"].id,
            currency_id=refs["currency_kzt"].id,
        )
    db.commit()

    headers = _headers_for_email(db, "accounting_admin@example.com")
    base = {"date_from": f"{year}-01-01", "date_to": f"{year}-12-31"}
    expected_counts = {"day": 4, "week": 3, "month": 3, "quarter": 2, "year": 1}
    for period, expected_total in expected_counts.items():
        response = client.get("/api/v1/cash-flow/bdds-report/by-periods", params={**base, "group_period": period}, headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["group_period"] == period
        assert body["total"] == expected_total


def test_bdds_report_diagnostics_and_pagination(client, db):
    refs = _report_refs(db)
    year = _unique_year(2070)
    cases = [
        (f"DIAG-NEEDS-{year}", f"{year}-01-01", "NeedsEnrichment", "Inflow", 10, refs["item_inflow"].id, refs["currency_kzt"].id, False),
        (f"DIAG-IGNORED-{year}", f"{year}-01-02", "Ignored", "Outflow", 11, refs["item_outflow"].id, refs["currency_kzt"].id, False),
        (f"DIAG-NO-DIRECTION-{year}", f"{year}-01-03", "Completed", None, 12, refs["item_inflow"].id, refs["currency_kzt"].id, False),
        ("DIAG-NO-DATE", None, "Completed", "Inflow", 13, refs["item_inflow"].id, refs["currency_kzt"].id, False),
        (f"DIAG-NO-AMOUNT-{year}", f"{year}-01-05", "Completed", "Inflow", 0, refs["item_inflow"].id, refs["currency_kzt"].id, False),
        (f"DIAG-NO-ITEM-{year}", f"{year}-01-06", "Completed", "Inflow", 14, None, refs["currency_kzt"].id, False),
        (f"DIAG-NO-CURRENCY-{year}", f"{year}-01-07", "Completed", "Inflow", 15, refs["item_inflow"].id, None, False),
        (f"DIAG-SOURCE-CHANGED-{year}", f"{year}-01-08", "Completed", "Inflow", 16, refs["item_inflow"].id, refs["currency_kzt"].id, True),
    ]
    for source_number, source_date, status, direction, amount, item_id, currency_id, source_changed in cases:
        _create_allocation(
            db,
            refs,
            source_number=source_number,
            source_date=source_date,
            allocation_status=status,
            direction=direction,
            amount=amount,
            organization_id=refs["org1"].id,
            project_id=refs["project_main"].id,
            cash_flow_item_id=item_id,
            cash_flow_operation_type_id=refs["operation_type"].id,
            currency_id=currency_id,
            source_changed=source_changed,
        )
    db.commit()

    headers = _headers_for_email(db, "accounting_admin@example.com")
    response = client.get(
        "/api/v1/cash-flow/bdds-report/diagnostics",
        params={"date_from": f"{year}-01-01", "date_to": f"{year}-12-31", "limit": 20, "offset": 0},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    returned_types = {item["diagnostic_type"] for item in body["items"]}
    assert {
        "needs_enrichment",
        "ignored",
        "missing_direction",
        "missing_date",
        "missing_amount",
        "missing_cash_flow_item",
        "missing_currency",
        "source_changed",
    }.issubset(returned_types)

    filtered = client.get(
        "/api/v1/cash-flow/bdds-report/diagnostics",
        params={"date_from": f"{year}-01-01", "date_to": f"{year}-12-31", "diagnostic_type": "source_changed", "limit": 20, "offset": 0},
        headers=headers,
    )
    assert filtered.status_code == 200, filtered.text
    filtered_body = filtered.json()
    assert filtered_body["total"] == 1
    assert filtered_body["items"][0]["source_document_number"] == f"DIAG-SOURCE-CHANGED-{year}"

    paged = client.get(
        "/api/v1/cash-flow/bdds-report/diagnostics",
        params={"date_from": f"{year}-01-01", "date_to": f"{year}-12-31", "limit": 1, "offset": 1},
        headers=headers,
    )
    assert paged.status_code == 200, paged.text
    paged_body = paged.json()
    assert paged_body["limit"] == 1
    assert paged_body["offset"] == 1
    assert paged_body["total"] >= 8
    assert len(paged_body["items"]) == 1
