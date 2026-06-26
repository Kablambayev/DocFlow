from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import status

from app.core.exceptions import AppError
from app.modules.audit.service import AuditService
from app.modules.comments.models import CommentType, DocumentComment
from app.modules.documents.models import DocumentApprovalStatus
from app.modules.notifications.models import NotificationType
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import NotificationService
from app.modules.workflow.matrix import MatrixEngine
from app.modules.workflow.models import ProcessStatus, TaskStatus
from app.modules.workflow.repository import WorkflowRepository
from app.modules.workflow.resolvers import ApproverResolver


class WorkflowEngine:
    def __init__(self, db, audit_service: AuditService):
        self.repository = WorkflowRepository(db)
        self.audit_service = audit_service
        self.matrix_engine = MatrixEngine()
        self.approver_resolver = ApproverResolver(self.repository)
        self.notification_service = NotificationService(NotificationRepository(db))

    def submit_document(self, document_id: UUID, user_id: UUID) -> None:
        document = self.repository.get_document(document_id)
        if document is None:
            raise AppError("Document not found", code="DOCUMENT_NOT_FOUND", status_code=404)
        if document.approval_status not in [DocumentApprovalStatus.DRAFT, DocumentApprovalStatus.WITHDRAWN]:
            raise AppError(
                "Document cannot be submitted in current status",
                code="DOCUMENT_SUBMIT_FORBIDDEN",
                status_code=status.HTTP_409_CONFLICT,
                details={"approval_status": document.approval_status},
            )
        active_process = self.repository.get_active_process_by_document_id(document_id)
        if active_process is not None:
            raise AppError("Active process already exists", code="PROCESS_ALREADY_RUNNING", status_code=409)

        route_version = self.resolve_route(document)
        process = self.start_process(document, route_version, user_id)
        document.approval_status = DocumentApprovalStatus.ON_APPROVAL
        self.notification_service.safe_create_notification(
            recipient_id=document.author_id,
            actor_id=user_id,
            notification_type=NotificationType.DOCUMENT_SUBMITTED,
            title="Документ отправлен на согласование",
            message=f"Документ {document.number} отправлен на согласование",
            entity_type="document",
            entity_id=document.id,
            document_id=document.id,
            payload={"document_number": document.number, "document_title": document.title, "process_id": str(process.id)},
        )
        self.repository.commit()
        self.audit_service.log("document", document.id, "document_submitted", user_id=user_id)

    def resolve_route(self, document):
        rules = self.repository.list_active_matrix_rules(document.document_type_id)
        route_id = self.matrix_engine.resolve_route_id(document, rules)
        route_version = self.repository.get_latest_published_route_version(route_id)
        if route_version is None:
            raise AppError(
                "Published route version not found",
                code="ROUTE_VERSION_NOT_FOUND",
                status_code=404,
                details={"route_id": str(route_id)},
            )
        return route_version

    def start_process(self, document, route_version, user_id: UUID):
        steps = sorted(route_version.route_schema_json.get("steps", []), key=lambda x: x.get("order", 0))
        if not steps:
            raise AppError("Route has no steps", code="ROUTE_HAS_NO_STEPS", status_code=409)

        first_step = steps[0]
        process = self.repository.create_process(document.id, route_version.id, user_id, first_step.get("order"))
        self.create_tasks_for_step(process, first_step, actor_id=user_id)
        return process

    def create_tasks_for_step(self, process, step, actor_id: UUID | None = None) -> list:
        resolver_config = step.get("approverResolver", {})
        approver_ids = self.approver_resolver.resolve(resolver_config)
        if not approver_ids:
            raise AppError(
                "No approvers resolved",
                code="NO_APPROVERS_RESOLVED",
                status_code=409,
                details={"step": step},
            )

        sla_hours = step.get("slaHours")
        due_at = datetime.now(timezone.utc) + timedelta(hours=sla_hours) if isinstance(sla_hours, int) else None

        document = self.repository.get_document(process.document_id)
        created_tasks = []
        for approver_id in set(approver_ids):
            task = self.repository.create_task(
                process_id=process.id,
                document_id=process.document_id,
                step_order=step.get("order", 0),
                step_name=step.get("name", "Approval step"),
                approver_id=approver_id,
                due_at=due_at,
            )
            created_tasks.append(task)
            if document is not None:
                self.notification_service.safe_create_notification(
                    recipient_id=task.approver_id,
                    actor_id=actor_id,
                    notification_type=NotificationType.APPROVAL_TASK_CREATED,
                    title="Новая задача согласования",
                    message=f"Вам назначена задача по документу {document.number}",
                    entity_type="task",
                    entity_id=task.id,
                    document_id=task.document_id,
                    task_id=task.id,
                    payload={
                        "document_number": document.number,
                        "document_title": document.title,
                        "step_name": task.step_name,
                        "step_order": task.step_order,
                    },
                )
        return created_tasks

    def approve_task(self, task_id: UUID, user_id: UUID, comment: str | None) -> None:
        task = self.repository.get_task(task_id)
        if task is None:
            raise AppError("Task not found", code="TASK_NOT_FOUND", status_code=404)
        if task.status != TaskStatus.PENDING:
            raise AppError("Task is not pending", code="TASK_NOT_PENDING", status_code=409)
        if task.approver_id != user_id:
            raise AppError("Task does not belong to user", code="TASK_ACCESS_DENIED", status_code=403)

        task.status = TaskStatus.APPROVED
        task.completed_at = datetime.now(timezone.utc)
        self.repository.create_decision(task.id, task.process_id, task.document_id, user_id, "Approve", comment)
        self._create_approval_comment(task.document_id, user_id, comment)

        process = self.repository.get_process(task.process_id)
        document = self.repository.get_document(task.document_id)
        if process is None:
            raise AppError("Process not found", code="PROCESS_NOT_FOUND", status_code=404)
        if document is None:
            raise AppError("Document not found", code="DOCUMENT_NOT_FOUND", status_code=404)

        self.audit_service.log("approval_task", task.id, "approval_task_approved", user_id=user_id)
        self.notification_service.safe_create_notification(
            recipient_id=document.author_id,
            actor_id=user_id,
            notification_type=NotificationType.APPROVAL_TASK_APPROVED,
            title="Задача согласована",
            message=f"{self.repository.get_user_name(user_id) or 'Согласующий'} согласовал задачу по документу {document.number}",
            entity_type="task",
            entity_id=task.id,
            document_id=document.id,
            task_id=task.id,
            payload={"document_number": document.number, "document_title": document.title, "step_name": task.step_name},
        )
        self.complete_step_if_possible(process, task.step_order, actor_id=user_id)
        if document.approval_status == DocumentApprovalStatus.APPROVED:
            self.notification_service.safe_create_notification(
                recipient_id=document.author_id,
                actor_id=user_id,
                notification_type=NotificationType.DOCUMENT_APPROVED,
                title="Документ согласован",
                message=f"Документ {document.number} полностью согласован",
                entity_type="document",
                entity_id=document.id,
                document_id=document.id,
                payload={"document_number": document.number, "document_title": document.title, "process_id": str(process.id)},
            )
        self.repository.commit()

    def reject_task(self, task_id: UUID, user_id: UUID, comment: str | None) -> None:
        if not comment or not comment.strip():
            raise AppError("Reject comment is required", code="REJECT_COMMENT_REQUIRED", status_code=400)
        task = self.repository.get_task(task_id)
        if task is None:
            raise AppError("Task not found", code="TASK_NOT_FOUND", status_code=404)
        if task.status != TaskStatus.PENDING:
            raise AppError("Task is not pending", code="TASK_NOT_PENDING", status_code=409)
        if task.approver_id != user_id:
            raise AppError("Task does not belong to user", code="TASK_ACCESS_DENIED", status_code=403)

        process = self.repository.get_process(task.process_id)
        document = self.repository.get_document(task.document_id)
        if process is None or document is None:
            raise AppError("Process or document not found", code="PROCESS_OR_DOCUMENT_NOT_FOUND", status_code=404)

        task.status = TaskStatus.REJECTED
        task.completed_at = datetime.now(timezone.utc)
        self.repository.create_decision(task.id, task.process_id, task.document_id, user_id, "Reject", comment)
        self._create_approval_comment(task.document_id, user_id, comment)

        process.status = ProcessStatus.REJECTED
        process.finished_at = datetime.now(timezone.utc)
        document.approval_status = DocumentApprovalStatus.REJECTED
        cancelled_tasks = self.repository.cancel_pending_tasks_for_process(process.id)
        self._notify_cancelled_tasks(cancelled_tasks, actor_id=user_id, document=document)

        self.audit_service.log("approval_task", task.id, "approval_task_rejected", user_id=user_id)
        self.audit_service.log("approval_process", process.id, "approval_process_rejected", user_id=user_id)
        self.notification_service.safe_create_notification(
            recipient_id=document.author_id,
            actor_id=user_id,
            notification_type=NotificationType.APPROVAL_TASK_REJECTED,
            title="Задача отклонена",
            message=f"{self.repository.get_user_name(user_id) or 'Согласующий'} отклонил задачу по документу {document.number}",
            entity_type="task",
            entity_id=task.id,
            document_id=document.id,
            task_id=task.id,
            payload={"document_number": document.number, "document_title": document.title, "step_name": task.step_name},
        )
        self.notification_service.safe_create_notification(
            recipient_id=document.author_id,
            actor_id=user_id,
            notification_type=NotificationType.DOCUMENT_REJECTED,
            title="Документ отклонен",
            message=f"Документ {document.number} отклонен",
            entity_type="document",
            entity_id=document.id,
            document_id=document.id,
            payload={"document_number": document.number, "document_title": document.title, "process_id": str(process.id)},
        )
        self.repository.commit()

    def complete_step_if_possible(self, process, step_order: int, actor_id: UUID | None = None) -> None:
        tasks = self.repository.list_tasks_for_step(process.id, step_order)
        if not tasks:
            return

        route_version = self.repository.get_route_version(process.route_version_id)
        if route_version is None:
            raise AppError("Route version not found", code="ROUTE_VERSION_NOT_FOUND", status_code=404)
        steps = route_version.route_schema_json.get("steps", [])
        step = next((item for item in steps if item.get("order") == step_order), None)
        if step is None:
            return

        policy = (step.get("decisionPolicy") or "all").lower()
        approved_count = len([t for t in tasks if t.status == TaskStatus.APPROVED])
        total_count = len(tasks)

        should_complete = approved_count >= 1 if policy == "any" else approved_count == total_count
        if should_complete:
            if policy == "any":
                document = self.repository.get_document(process.document_id)
                cancelled_tasks = []
                for item in tasks:
                    if item.status == TaskStatus.PENDING:
                        item.status = TaskStatus.CANCELLED
                        item.completed_at = datetime.now(timezone.utc)
                        cancelled_tasks.append(item)
                if document is not None:
                    self._notify_cancelled_tasks(cancelled_tasks, actor_id=actor_id, document=document)
            self.move_to_next_step(process, actor_id=actor_id)

    def move_to_next_step(self, process, actor_id: UUID | None = None) -> None:
        route_version = self.repository.get_route_version(process.route_version_id)
        if route_version is None:
            raise AppError("Route version not found", code="ROUTE_VERSION_NOT_FOUND", status_code=404)

        steps = sorted(route_version.route_schema_json.get("steps", []), key=lambda x: x.get("order", 0))
        current_order = process.current_step_order or 0
        next_step = next((step for step in steps if step.get("order", 0) > current_order), None)

        if next_step is None:
            self.finish_process(process)
            return

        process.current_step_order = next_step.get("order")
        self.create_tasks_for_step(process, next_step, actor_id=actor_id)

    def finish_process(self, process) -> None:
        document = self.repository.get_document(process.document_id)
        if document is None:
            raise AppError("Document not found", code="DOCUMENT_NOT_FOUND", status_code=404)

        process.status = ProcessStatus.APPROVED
        process.finished_at = datetime.now(timezone.utc)
        document.approval_status = DocumentApprovalStatus.APPROVED
        self.audit_service.log("approval_process", process.id, "approval_process_approved", user_id=process.started_by)

    def cancel_process(self, process) -> None:
        document = self.repository.get_document(process.document_id)
        process.status = ProcessStatus.CANCELLED
        process.finished_at = datetime.now(timezone.utc)
        if document is not None:
            document.approval_status = DocumentApprovalStatus.WITHDRAWN
        cancelled_tasks = self.repository.cancel_pending_tasks_for_process(process.id)
        if document is not None:
            self._notify_cancelled_tasks(cancelled_tasks, actor_id=None, document=document)

    def _create_approval_comment(self, document_id: UUID, user_id: UUID, comment: str | None) -> None:
        if not comment or not comment.strip():
            return
        self.repository.db.add(
            DocumentComment(
                document_id=document_id,
                author_id=user_id,
                comment_text=comment.strip(),
                comment_type=CommentType.APPROVAL,
            )
        )

    def _notify_cancelled_tasks(self, tasks, actor_id: UUID | None, document) -> None:
        for task in tasks:
            self.notification_service.safe_create_notification(
                recipient_id=task.approver_id,
                actor_id=actor_id,
                notification_type=NotificationType.APPROVAL_TASK_CANCELLED,
                title="Задача отменена",
                message=f"Задача по документу {document.number} отменена",
                entity_type="task",
                entity_id=task.id,
                document_id=document.id,
                task_id=task.id,
                payload={"document_number": document.number, "document_title": document.title, "step_name": task.step_name},
            )
