from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AppError
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.workflow.engine import WorkflowEngine
from app.modules.workflow.repository import WorkflowRepository
from app.modules.workflow.schemas import (
    ApprovalMatrixRuleCreate,
    ApprovalMatrixRuleUpdate,
    ApprovalRouteCreate,
    ApprovalRouteVersionCreate,
    ApprovalRouteVersionUpdate,
)


class WorkflowService:
    def __init__(self, repository: WorkflowRepository):
        self.repository = repository
        self.audit_service = AuditService(AuditRepository(self.repository.db))

    def list_my_tasks(self, user_id: UUID):
        return self.repository.list_pending_tasks_for_user(user_id)

    def approve_task(self, task_id: UUID, user_id: UUID, comment: str | None):
        engine = WorkflowEngine(self.repository.db, self.audit_service)
        engine.approve_task(task_id, user_id, comment)
        task = self.repository.get_task(task_id)
        if task is None:
            raise AppError("Task not found", code="TASK_NOT_FOUND", status_code=404)
        return task

    def reject_task(self, task_id: UUID, user_id: UUID, comment: str | None):
        engine = WorkflowEngine(self.repository.db, self.audit_service)
        engine.reject_task(task_id, user_id, comment)
        task = self.repository.get_task(task_id)
        if task is None:
            raise AppError("Task not found", code="TASK_NOT_FOUND", status_code=404)
        return task

    def list_routes(self):
        return self.repository.list_routes()

    def create_route(self, payload: ApprovalRouteCreate):
        return self.repository.create_route(payload)

    def get_route(self, route_id: UUID):
        route = self.repository.get_route(route_id)
        if route is None:
            raise AppError("Route not found", code="ROUTE_NOT_FOUND", status_code=404)
        return route

    def create_route_version(self, route_id: UUID, payload: ApprovalRouteVersionCreate):
        _ = self.get_route(route_id)
        return self.repository.create_route_version(route_id, payload)

    def list_route_versions(self, route_id: UUID):
        _ = self.get_route(route_id)
        return self.repository.list_route_versions(route_id)

    def get_route_version(self, version_id: UUID):
        version = self.repository.get_route_version_by_id(version_id)
        if version is None:
            raise AppError("Route version not found", code="ROUTE_VERSION_NOT_FOUND", status_code=404)
        return version

    def update_route_version(self, version_id: UUID, payload: ApprovalRouteVersionUpdate, user_id: UUID | None):
        version = self.get_route_version(version_id)
        if version.status != "draft":
            raise AppError("Only draft version can be edited", code="INVALID_ROUTE_VERSION_STATE", status_code=409)
        updated = self.repository.update_route_version(version, payload)
        self.audit_service.log("approval_route_version", updated.id, "approval_route_version_updated", user_id=user_id)
        return updated

    def publish_route_version(self, version_id: UUID, user_id: UUID | None):
        version = self.repository.get_route_version_by_id(version_id)
        if version is None:
            raise AppError("Route version not found", code="ROUTE_VERSION_NOT_FOUND", status_code=404)
        if version.status != "draft":
            raise AppError("Only draft version can be published", code="INVALID_ROUTE_VERSION_STATE", status_code=409)

        result = self.repository.publish_route_version(version)
        self.audit_service.log("approval_route_version", result.id, "route_version_published", user_id=user_id)
        return result

    def list_matrix_rules(self):
        return self.repository.list_matrix_rules()

    def create_matrix_rule(self, payload: ApprovalMatrixRuleCreate, user_id: UUID | None):
        rule = self.repository.create_matrix_rule(payload)
        self.audit_service.log("approval_matrix_rule", rule.id, "matrix_rule_created", user_id=user_id)
        return rule

    def update_matrix_rule(self, rule_id: UUID, payload: ApprovalMatrixRuleUpdate, user_id: UUID | None):
        rule = self.repository.get_matrix_rule(rule_id)
        if rule is None:
            raise AppError("Matrix rule not found", code="MATRIX_RULE_NOT_FOUND", status_code=404)
        updated = self.repository.update_matrix_rule(rule, payload)
        self.audit_service.log("approval_matrix_rule", updated.id, "matrix_rule_updated", user_id=user_id)
        return updated

    def delete_matrix_rule(self, rule_id: UUID, user_id: UUID | None):
        rule = self.repository.get_matrix_rule(rule_id)
        if rule is None:
            raise AppError("Matrix rule not found", code="MATRIX_RULE_NOT_FOUND", status_code=404)
        deleted = self.repository.soft_delete_matrix_rule(rule)
        self.audit_service.log("approval_matrix_rule", deleted.id, "matrix_rule_deleted", user_id=user_id)
        return deleted

