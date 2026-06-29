from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounting.models import (
    AccountingCashFlowItem,
    AccountingCashFlowOperationType,
    AccountingCounterparty,
    AccountingCounterpartyContract,
    AccountingCurrency,
    AccountingOrganization,
    AccountingProject,
)
from app.modules.cash_flow.mapping_models import CashFlowMappingRule, CashFlowMappingRuleField


class CashFlowMappingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_rules(self, source_document_type_1c: str | None, cash_flow_direction: str | None, is_active: bool | None):
        fields_count = (
            select(func.count(CashFlowMappingRuleField.id))
            .where(CashFlowMappingRuleField.rule_id == CashFlowMappingRule.id)
            .scalar_subquery()
        )
        stmt = select(CashFlowMappingRule, fields_count.label("fields_count"))
        if source_document_type_1c:
            stmt = stmt.where(CashFlowMappingRule.source_document_type_1c == source_document_type_1c)
        if cash_flow_direction:
            stmt = stmt.where(CashFlowMappingRule.cash_flow_direction == cash_flow_direction)
        if is_active is not None:
            stmt = stmt.where(CashFlowMappingRule.is_active.is_(is_active))
        stmt = stmt.order_by(CashFlowMappingRule.priority.asc(), CashFlowMappingRule.name.asc())
        return self.db.execute(stmt).all()

    def get_rule(self, rule_id: UUID):
        stmt: Select[tuple[CashFlowMappingRule]] = (
            select(CashFlowMappingRule)
            .options(selectinload(CashFlowMappingRule.fields))
            .where(CashFlowMappingRule.id == rule_id)
        )
        return self.db.scalar(stmt)

    def create_rule(self, payload: dict):
        item = CashFlowMappingRule(**payload)
        self.db.add(item)
        self.db.flush()
        return item

    def delete_rule(self, item: CashFlowMappingRule):
        self.db.delete(item)
        self.db.flush()

    def save(self, item):
        self.db.add(item)
        self.db.flush()
        return item

    def find_rule_for_source(
        self,
        *,
        source_system: str,
        source_document_type_1c: str,
        source_document_type_code: str | None = None,
        cash_flow_direction: str | None = None,
    ):
        stmt: Select[tuple[CashFlowMappingRule]] = (
            select(CashFlowMappingRule)
            .options(selectinload(CashFlowMappingRule.fields))
            .where(
                CashFlowMappingRule.source_system == source_system,
                CashFlowMappingRule.source_document_type_1c == source_document_type_1c,
                CashFlowMappingRule.is_active.is_(True),
            )
            .order_by(CashFlowMappingRule.priority.asc(), CashFlowMappingRule.created_at.asc())
        )
        if source_document_type_code is not None:
            stmt = stmt.where(CashFlowMappingRule.source_document_type_code == source_document_type_code)
        if cash_flow_direction is not None:
            stmt = stmt.where(CashFlowMappingRule.cash_flow_direction == cash_flow_direction)
        return self.db.scalar(stmt)

    def lookup_dictionary_item(self, dictionary_type: str, lookup_by: str, value: str):
        model_map = {
            "organization": AccountingOrganization,
            "counterparty": AccountingCounterparty,
            "contract": AccountingCounterpartyContract,
            "currency": AccountingCurrency,
            "project": AccountingProject,
            "cash_flow_operation_type": AccountingCashFlowOperationType,
            "cash_flow_item": AccountingCashFlowItem,
        }
        field_map = {
            "external_id": "external_id",
            "code": "code",
            "name": "name",
        }
        model = model_map[dictionary_type]
        column_name = field_map[lookup_by]
        column = getattr(model, column_name)
        stmt = select(model).where(func.lower(column) == str(value).lower())
        if hasattr(model, "is_active"):
            stmt = stmt.where(model.is_active.is_(True))
        return self.db.scalar(stmt)
