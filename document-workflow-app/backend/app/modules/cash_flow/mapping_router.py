from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.db.session import get_db
from app.modules.cash_flow.mapping_repository import CashFlowMappingRepository
from app.modules.cash_flow.mapping_schemas import (
    CashFlowMappingResult,
    CashFlowMappingRuleCreate,
    CashFlowMappingRuleListItem,
    CashFlowMappingRuleRead,
    CashFlowMappingRuleUpdate,
    CashFlowMappingTestRequest,
)
from app.modules.cash_flow.mapping_service import CashFlowMappingService
from app.modules.users.models import User

router = APIRouter(prefix="/cash-flow", tags=["cash-flow"])


def get_service(db: Session = Depends(get_db)) -> CashFlowMappingService:
    return CashFlowMappingService(CashFlowMappingRepository(db))


@router.get("/mapping-rules", response_model=list[CashFlowMappingRuleListItem])
def list_mapping_rules(
    source_document_type_1c: str | None = None,
    cash_flow_direction: str | None = None,
    is_active: bool | None = None,
    _: User = Depends(require_permission("cash_flow.mapping.read")),
    service: CashFlowMappingService = Depends(get_service),
):
    return service.list_rules(source_document_type_1c, cash_flow_direction, is_active)


@router.get("/mapping-rules/{rule_id}", response_model=CashFlowMappingRuleRead)
def get_mapping_rule(
    rule_id: UUID,
    _: User = Depends(require_permission("cash_flow.mapping.read")),
    service: CashFlowMappingService = Depends(get_service),
):
    return service.get_rule(rule_id)


@router.post("/mapping-rules", response_model=CashFlowMappingRuleRead)
def create_mapping_rule(
    payload: CashFlowMappingRuleCreate,
    _: User = Depends(require_permission("cash_flow.mapping.manage")),
    service: CashFlowMappingService = Depends(get_service),
):
    return service.create_rule(payload)


@router.put("/mapping-rules/{rule_id}", response_model=CashFlowMappingRuleRead)
def update_mapping_rule(
    rule_id: UUID,
    payload: CashFlowMappingRuleUpdate,
    _: User = Depends(require_permission("cash_flow.mapping.manage")),
    service: CashFlowMappingService = Depends(get_service),
):
    return service.update_rule(rule_id, payload)


@router.delete("/mapping-rules/{rule_id}", status_code=204)
def delete_mapping_rule(
    rule_id: UUID,
    _: User = Depends(require_permission("cash_flow.mapping.manage")),
    service: CashFlowMappingService = Depends(get_service),
):
    service.delete_rule(rule_id)


@router.post("/mapping-rules/{rule_id}/test", response_model=CashFlowMappingResult)
def test_mapping_rule(
    rule_id: UUID,
    payload: CashFlowMappingTestRequest,
    _: User = Depends(require_permission("cash_flow.mapping.manage")),
    service: CashFlowMappingService = Depends(get_service),
):
    return service.test_mapping_rule(rule_id, payload.source_payload)
