from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.roles.models import Role
from app.modules.users.models import User
from app.modules.workflow.models import (
    ApprovalDecision,
    ApprovalMatrixRule,
    ApprovalProcess,
    ApprovalRoute,
    ApprovalRouteVersion,
    ApprovalTask,
    ProcessStatus,
    TaskStatus,
)
from app.modules.workflow.schemas import (
    ApprovalMatrixRuleCreate,
    ApprovalMatrixRuleUpdate,
    ApprovalRouteCreate,
    ApprovalRouteVersionCreate,
    ApprovalRouteVersionUpdate,
)


class WorkflowRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_document(self, document_id: UUID):
        from app.modules.documents.models import Document

        return self.db.get(Document, document_id)

    def get_task(self, task_id: UUID) -> ApprovalTask | None:
        return self.db.get(ApprovalTask, task_id)

    def get_process(self, process_id: UUID) -> ApprovalProcess | None:
        return self.db.get(ApprovalProcess, process_id)

    def get_active_process_by_document_id(self, document_id: UUID) -> ApprovalProcess | None:
        return self.db.scalar(
            select(ApprovalProcess).where(
                ApprovalProcess.document_id == document_id,
                ApprovalProcess.status == ProcessStatus.RUNNING,
            )
        )

    def get_route_version(self, route_version_id: UUID) -> ApprovalRouteVersion | None:
        return self.db.get(ApprovalRouteVersion, route_version_id)

    def list_pending_tasks_for_user(self, user_id: UUID) -> list[ApprovalTask]:
        return list(
            self.db.scalars(
                select(ApprovalTask)
                .where(ApprovalTask.approver_id == user_id, ApprovalTask.status == TaskStatus.PENDING)
                .order_by(ApprovalTask.created_at.asc())
            )
        )

    def list_active_matrix_rules(self, document_type_id: UUID) -> list[ApprovalMatrixRule]:
        return list(
            self.db.scalars(
                select(ApprovalMatrixRule)
                .where(ApprovalMatrixRule.document_type_id == document_type_id, ApprovalMatrixRule.is_active.is_(True))
                .order_by(ApprovalMatrixRule.priority.asc())
            )
        )

    def get_latest_published_route_version(self, route_id: UUID) -> ApprovalRouteVersion | None:
        return self.db.scalar(
            select(ApprovalRouteVersion)
            .where(ApprovalRouteVersion.route_id == route_id, ApprovalRouteVersion.status == "published")
            .order_by(ApprovalRouteVersion.version_number.desc())
        )

    def create_process(self, document_id: UUID, route_version_id: UUID, started_by: UUID, current_step_order: int | None) -> ApprovalProcess:
        process = ApprovalProcess(
            document_id=document_id,
            route_version_id=route_version_id,
            status=ProcessStatus.RUNNING,
            current_step_order=current_step_order,
            started_by=started_by,
            started_at=datetime.now(timezone.utc),
            finished_at=None,
        )
        self.db.add(process)
        self.db.flush()
        return process

    def create_task(
        self,
        process_id: UUID,
        document_id: UUID,
        step_order: int,
        step_name: str,
        approver_id: UUID,
        due_at: datetime | None,
    ) -> ApprovalTask:
        task = ApprovalTask(
            process_id=process_id,
            document_id=document_id,
            step_order=step_order,
            step_name=step_name,
            approver_id=approver_id,
            status=TaskStatus.PENDING,
            due_at=due_at,
            created_at=datetime.now(timezone.utc),
            completed_at=None,
        )
        self.db.add(task)
        self.db.flush()
        return task

    def create_decision(
        self,
        task_id: UUID,
        process_id: UUID,
        document_id: UUID,
        approver_id: UUID,
        decision: str,
        comment: str | None,
    ) -> ApprovalDecision:
        decision_row = ApprovalDecision(
            task_id=task_id,
            process_id=process_id,
            document_id=document_id,
            approver_id=approver_id,
            decision=decision,
            comment=comment,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(decision_row)
        self.db.flush()
        return decision_row

    def list_tasks_for_step(self, process_id: UUID, step_order: int) -> list[ApprovalTask]:
        return list(
            self.db.scalars(select(ApprovalTask).where(ApprovalTask.process_id == process_id, ApprovalTask.step_order == step_order))
        )

    def cancel_pending_tasks_for_process(self, process_id: UUID) -> None:
        pending_tasks = list(
            self.db.scalars(
                select(ApprovalTask).where(ApprovalTask.process_id == process_id, ApprovalTask.status == TaskStatus.PENDING)
            )
        )
        for task in pending_tasks:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, instance) -> None:
        self.db.refresh(instance)

    def list_routes(self) -> list[ApprovalRoute]:
        return list(self.db.scalars(select(ApprovalRoute).order_by(ApprovalRoute.created_at.desc())))

    def get_route(self, route_id: UUID) -> ApprovalRoute | None:
        return self.db.get(ApprovalRoute, route_id)

    def create_route(self, payload: ApprovalRouteCreate) -> ApprovalRoute:
        route = ApprovalRoute(**payload.model_dump())
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        return route

    def create_route_version(self, route_id: UUID, payload: ApprovalRouteVersionCreate) -> ApprovalRouteVersion:
        max_version = self.db.scalar(
            select(func.max(ApprovalRouteVersion.version_number)).where(ApprovalRouteVersion.route_id == route_id)
        )
        version = ApprovalRouteVersion(
            route_id=route_id,
            version_number=(max_version or 0) + 1,
            status="draft",
            route_schema_json=payload.route_schema_json,
            published_at=None,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def list_route_versions(self, route_id: UUID) -> list[ApprovalRouteVersion]:
        return list(
            self.db.scalars(
                select(ApprovalRouteVersion)
                .where(ApprovalRouteVersion.route_id == route_id)
                .order_by(ApprovalRouteVersion.version_number.desc())
            )
        )

    def get_route_version_by_id(self, version_id: UUID) -> ApprovalRouteVersion | None:
        return self.db.get(ApprovalRouteVersion, version_id)

    def update_route_version(
        self, version: ApprovalRouteVersion, payload: ApprovalRouteVersionUpdate
    ) -> ApprovalRouteVersion:
        version.route_schema_json = payload.route_schema_json
        self.db.commit()
        self.db.refresh(version)
        return version

    def publish_route_version(self, version: ApprovalRouteVersion) -> ApprovalRouteVersion:
        published_versions = list(
            self.db.scalars(
                select(ApprovalRouteVersion).where(
                    ApprovalRouteVersion.route_id == version.route_id,
                    ApprovalRouteVersion.status == "published",
                )
            )
        )
        for prev in published_versions:
            prev.status = "archived"

        version.status = "published"
        version.published_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(version)
        return version

    def list_matrix_rules(self) -> list[ApprovalMatrixRule]:
        return list(self.db.scalars(select(ApprovalMatrixRule).order_by(ApprovalMatrixRule.priority.asc())))

    def get_matrix_rule(self, rule_id: UUID) -> ApprovalMatrixRule | None:
        return self.db.get(ApprovalMatrixRule, rule_id)

    def create_matrix_rule(self, payload: ApprovalMatrixRuleCreate) -> ApprovalMatrixRule:
        rule = ApprovalMatrixRule(**payload.model_dump())
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_matrix_rule(self, rule: ApprovalMatrixRule, payload: ApprovalMatrixRuleUpdate) -> ApprovalMatrixRule:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, key, value)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def soft_delete_matrix_rule(self, rule: ApprovalMatrixRule) -> ApprovalMatrixRule:
        rule.is_active = False
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def find_active_users_by_role_code(self, role_code: str) -> list[UUID]:
        stmt = (
            select(User.id)
            .join(User.roles)
            .where(Role.code == role_code, Role.is_active.is_(True), User.is_active.is_(True))
            .distinct()
        )
        return list(self.db.scalars(stmt))

