from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.session import get_db
from app.modules.workflow.repository import WorkflowRepository
from app.modules.workflow.schemas import (
	ApprovalMatrixRuleCreate,
	ApprovalMatrixRuleRead,
	ApprovalMatrixRuleUpdate,
	ApprovalRouteCreate,
	ApprovalRouteRead,
	ApprovalRouteVersionCreate,
	ApprovalRouteVersionRead,
	ApprovalRouteVersionUpdate,
	TaskDecisionRequest,
	WorkflowTaskRead,
)
from app.modules.workflow.service import WorkflowService

router = APIRouter(prefix="/workflow", tags=["workflow"])


def get_service(db: Session = Depends(get_db)) -> WorkflowService:
	return WorkflowService(WorkflowRepository(db))


def get_user_id_header(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> UUID:
	if x_user_id is None:
		raise AppError("X-User-Id header is required", code="UNAUTHORIZED", status_code=401)
	return UUID(x_user_id)


@router.get("/tasks/my", response_model=list[WorkflowTaskRead])
def get_my_tasks(
	user_id: UUID = Depends(get_user_id_header),
	service: WorkflowService = Depends(get_service),
) -> list[WorkflowTaskRead]:
	return service.list_my_tasks(user_id)


@router.post("/tasks/{id}/approve", response_model=WorkflowTaskRead)
def approve_task(
	id: UUID,
	payload: TaskDecisionRequest,
	user_id: UUID = Depends(get_user_id_header),
	service: WorkflowService = Depends(get_service),
) -> WorkflowTaskRead:
	return service.approve_task(id, user_id, payload.comment)


@router.post("/tasks/{id}/reject", response_model=WorkflowTaskRead)
def reject_task(
	id: UUID,
	payload: TaskDecisionRequest,
	user_id: UUID = Depends(get_user_id_header),
	service: WorkflowService = Depends(get_service),
) -> WorkflowTaskRead:
	return service.reject_task(id, user_id, payload.comment)


@router.get("/routes", response_model=list[ApprovalRouteRead])
def list_routes(service: WorkflowService = Depends(get_service)) -> list[ApprovalRouteRead]:
	return service.list_routes()


@router.post("/routes", response_model=ApprovalRouteRead)
def create_route(payload: ApprovalRouteCreate, service: WorkflowService = Depends(get_service)) -> ApprovalRouteRead:
	return service.create_route(payload)


@router.get("/routes/{id}", response_model=ApprovalRouteRead)
def get_route(id: UUID, service: WorkflowService = Depends(get_service)) -> ApprovalRouteRead:
	return service.get_route(id)


@router.post("/routes/{id}/versions", response_model=ApprovalRouteVersionRead)
def create_route_version(
	id: UUID,
	payload: ApprovalRouteVersionCreate,
	service: WorkflowService = Depends(get_service),
) -> ApprovalRouteVersionRead:
	return service.create_route_version(id, payload)


@router.get("/routes/{id}/versions", response_model=list[ApprovalRouteVersionRead])
def list_route_versions(
	id: UUID,
	service: WorkflowService = Depends(get_service),
) -> list[ApprovalRouteVersionRead]:
	return service.list_route_versions(id)


@router.get("/route-versions/{id}", response_model=ApprovalRouteVersionRead)
def get_route_version(
	id: UUID,
	service: WorkflowService = Depends(get_service),
) -> ApprovalRouteVersionRead:
	return service.get_route_version(id)


@router.put("/route-versions/{id}", response_model=ApprovalRouteVersionRead)
def update_route_version(
	id: UUID,
	payload: ApprovalRouteVersionUpdate,
	user_id: UUID = Depends(get_user_id_header),
	service: WorkflowService = Depends(get_service),
) -> ApprovalRouteVersionRead:
	return service.update_route_version(id, payload, user_id)


@router.post("/route-versions/{id}/publish", response_model=ApprovalRouteVersionRead)
def publish_route_version(
	id: UUID,
	user_id: UUID = Depends(get_user_id_header),
	service: WorkflowService = Depends(get_service),
) -> ApprovalRouteVersionRead:
	return service.publish_route_version(id, user_id)


@router.get("/matrix-rules", response_model=list[ApprovalMatrixRuleRead])
def list_matrix_rules(service: WorkflowService = Depends(get_service)) -> list[ApprovalMatrixRuleRead]:
	return service.list_matrix_rules()


@router.post("/matrix-rules", response_model=ApprovalMatrixRuleRead)
def create_matrix_rule(
	payload: ApprovalMatrixRuleCreate,
	user_id: UUID = Depends(get_user_id_header),
	service: WorkflowService = Depends(get_service),
) -> ApprovalMatrixRuleRead:
	return service.create_matrix_rule(payload, user_id)


@router.put("/matrix-rules/{id}", response_model=ApprovalMatrixRuleRead)
def update_matrix_rule(
	id: UUID,
	payload: ApprovalMatrixRuleUpdate,
	user_id: UUID = Depends(get_user_id_header),
	service: WorkflowService = Depends(get_service),
) -> ApprovalMatrixRuleRead:
	return service.update_matrix_rule(id, payload, user_id)


@router.delete("/matrix-rules/{id}", response_model=ApprovalMatrixRuleRead)
def delete_matrix_rule(
	id: UUID,
	user_id: UUID = Depends(get_user_id_header),
	service: WorkflowService = Depends(get_service),
) -> ApprovalMatrixRuleRead:
	return service.delete_matrix_rule(id, user_id)

