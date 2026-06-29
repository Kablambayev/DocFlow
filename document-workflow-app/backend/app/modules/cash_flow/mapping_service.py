from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.modules.cash_flow.mapping_models import CashFlowMappingRuleField
from app.modules.cash_flow.mapping_repository import CashFlowMappingRepository
from app.modules.cash_flow.mapping_schemas import (
    DICTIONARY_TYPES,
    LOOKUP_BY_VALUES,
    MAPPING_TYPES,
    REQUIRED_COMPLETED_FIELDS,
    CashFlowMappingFieldResult,
    CashFlowMappingResult,
    CashFlowMappingRuleCreate,
    CashFlowMappingRuleRead,
    CashFlowMappingRuleUpdate,
)

ALLOCATION_STATUS_VALUES = {"NeedsEnrichment", "Completed", "Ignored", "Draft"}


class CashFlowMappingService:
    def __init__(self, repository: CashFlowMappingRepository):
        self.repository = repository

    def list_rules(self, source_document_type_1c: str | None, cash_flow_direction: str | None, is_active: bool | None):
        rows = self.repository.list_rules(source_document_type_1c, cash_flow_direction, is_active)
        return [
            {
                **rule.__dict__,
                "fields_count": fields_count,
            }
            for rule, fields_count in rows
        ]

    def get_rule(self, rule_id: UUID):
        rule = self.repository.get_rule(rule_id)
        if rule is None:
            raise AppError("Mapping rule not found", code="CASH_FLOW_MAPPING_RULE_NOT_FOUND", status_code=404)
        return rule

    def create_rule(self, payload: CashFlowMappingRuleCreate):
        self._validate_fields(payload.fields)
        try:
            rule = self.repository.create_rule(payload.model_dump(exclude={"fields"}))
            self._replace_fields(rule, payload.fields)
            return self._commit_refresh(rule)
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise AppError(
                "Mapping rule conflicts with an existing priority for this source document",
                code="CASH_FLOW_MAPPING_RULE_CONFLICT",
                status_code=status.HTTP_409_CONFLICT,
            ) from exc

    def update_rule(self, rule_id: UUID, payload: CashFlowMappingRuleUpdate):
        rule = self.get_rule(rule_id)
        try:
            for key, value in payload.model_dump(exclude_unset=True, exclude={"fields"}).items():
                setattr(rule, key, value)
            if payload.fields is not None:
                self._validate_fields(payload.fields)
                self._replace_fields(rule, payload.fields)
            return self._commit_refresh(rule)
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise AppError(
                "Mapping rule conflicts with an existing priority for this source document",
                code="CASH_FLOW_MAPPING_RULE_CONFLICT",
                status_code=status.HTTP_409_CONFLICT,
            ) from exc

    def delete_rule(self, rule_id: UUID):
        rule = self.get_rule(rule_id)
        self.repository.delete_rule(rule)
        self.repository.db.commit()

    def test_mapping_rule(self, rule_id: UUID, source_payload: dict[str, Any]) -> CashFlowMappingResult:
        rule = self.get_rule(rule_id)
        return self._execute_mapping(rule, source_payload)

    def apply_mapping_rule(self, rule_id: UUID, source_payload: dict[str, Any]) -> CashFlowMappingResult:
        rule = self.get_rule(rule_id)
        return self._execute_mapping(rule, source_payload)

    def find_rule_for_source(
        self,
        source_system: str,
        source_document_type_1c: str,
        source_document_type_code: str | None = None,
        cash_flow_direction: str | None = None,
    ):
        return self.repository.find_rule_for_source(
            source_system=source_system,
            source_document_type_1c=source_document_type_1c,
            source_document_type_code=source_document_type_code,
            cash_flow_direction=cash_flow_direction,
        )

    def _commit_refresh(self, rule):
        self.repository.db.commit()
        self.repository.db.refresh(rule)
        return self.get_rule(rule.id)

    def _replace_fields(self, rule, fields):
        existing_by_id = {item.id: item for item in rule.fields}
        next_fields: list[CashFlowMappingRuleField] = []
        keep_ids = set()
        for field in fields:
            payload = field.model_dump(exclude={"id"})
            if field.id is not None and field.id in existing_by_id:
                item = existing_by_id[field.id]
                for key, value in payload.items():
                    setattr(item, key, value)
                keep_ids.add(item.id)
                next_fields.append(item)
                continue
            item = CashFlowMappingRuleField(rule_id=rule.id, **payload)
            self.repository.db.add(item)
            self.repository.db.flush()
            next_fields.append(item)
        for item in list(rule.fields):
            if item.id not in keep_ids and item not in next_fields:
                self.repository.db.delete(item)
        rule.fields = sorted(next_fields, key=lambda item: item.sort_order)
        self.repository.save(rule)

    def _validate_fields(self, fields):
        for field in fields:
            if field.mapping_type not in MAPPING_TYPES:
                raise AppError("Unsupported mapping_type", code="CASH_FLOW_MAPPING_FIELD_INVALID", status_code=422)
            if field.mapping_type == "dictionary_lookup":
                if field.dictionary_type not in DICTIONARY_TYPES:
                    raise AppError("Unsupported dictionary_type", code="CASH_FLOW_MAPPING_FIELD_INVALID", status_code=422)
                if field.lookup_by not in LOOKUP_BY_VALUES:
                    raise AppError("Unsupported lookup_by", code="CASH_FLOW_MAPPING_FIELD_INVALID", status_code=422)

    def _execute_mapping(self, rule, source_payload: dict[str, Any]) -> CashFlowMappingResult:
        mapped_data: dict[str, Any] = {}
        field_results: list[CashFlowMappingFieldResult] = []
        for field in rule.fields:
            result = self._map_field(field, source_payload)
            field_results.append(result)
            if result.mapped_value is not None:
                mapped_data[field.target_field] = result.mapped_value

        missing_required_fields = sorted(
            {
                field_name
                for field_name in REQUIRED_COMPLETED_FIELDS
                if mapped_data.get(field_name) in (None, "", [], {})
            }
        )
        explicit_status = mapped_data.get("allocation_status")
        if missing_required_fields:
            allocation_status = "NeedsEnrichment"
        elif explicit_status in ALLOCATION_STATUS_VALUES:
            allocation_status = explicit_status
        else:
            allocation_status = "Completed"

        mapped_data["allocation_status"] = allocation_status
        mapped_data["mapping_rule_id"] = str(rule.id)
        mapped_data["mapping_result"] = allocation_status
        mapped_data["missing_required_fields"] = missing_required_fields

        status_value = "Failed" if any(item.status == "error" for item in field_results) else allocation_status
        return CashFlowMappingResult(
            rule_id=rule.id,
            status=status_value,
            mapped_data=mapped_data,
            missing_required_fields=missing_required_fields,
            field_results=field_results,
        )

    def _map_field(self, field, source_payload: dict[str, Any]) -> CashFlowMappingFieldResult:
        if field.mapping_type == "constant":
            return CashFlowMappingFieldResult(
                target_field=field.target_field,
                mapping_type=field.mapping_type,
                source_path=field.source_path,
                mapped_value=field.constant_value,
                status="constant",
                message="Constant value applied",
            )

        if field.mapping_type == "path":
            found, value = self._extract_path(source_payload, field.source_path)
            return CashFlowMappingFieldResult(
                target_field=field.target_field,
                mapping_type=field.mapping_type,
                source_path=field.source_path,
                source_value=value,
                mapped_value=value if found else None,
                status="mapped" if found else "missing",
                message=None if found else "Source path not found",
            )

        if field.mapping_type == "default":
            found, value = self._extract_path(source_payload, field.source_path)
            if found and value not in (None, "", [], {}):
                return CashFlowMappingFieldResult(
                    target_field=field.target_field,
                    mapping_type=field.mapping_type,
                    source_path=field.source_path,
                    source_value=value,
                    mapped_value=value,
                    status="mapped",
                )
            return CashFlowMappingFieldResult(
                target_field=field.target_field,
                mapping_type=field.mapping_type,
                source_path=field.source_path,
                source_value=value,
                mapped_value=field.default_value,
                status="defaulted" if field.default_value is not None else "missing",
                message="Default value applied" if field.default_value is not None else "Source path not found",
            )

        if field.mapping_type == "dictionary_lookup":
            found, value = self._extract_path(source_payload, field.source_path)
            if not found or value in (None, "", [], {}):
                return CashFlowMappingFieldResult(
                    target_field=field.target_field,
                    mapping_type=field.mapping_type,
                    source_path=field.source_path,
                    source_value=value,
                    status="missing",
                    message="Source path not found",
                )
            try:
                item = self.repository.lookup_dictionary_item(field.dictionary_type, field.lookup_by, str(value))
            except Exception as exc:
                return CashFlowMappingFieldResult(
                    target_field=field.target_field,
                    mapping_type=field.mapping_type,
                    source_path=field.source_path,
                    source_value=value,
                    status="error",
                    message=str(exc),
                )
            if item is None:
                return CashFlowMappingFieldResult(
                    target_field=field.target_field,
                    mapping_type=field.mapping_type,
                    source_path=field.source_path,
                    source_value=value,
                    status="missing",
                    message="Dictionary item not found",
                )
            return CashFlowMappingFieldResult(
                target_field=field.target_field,
                mapping_type=field.mapping_type,
                source_path=field.source_path,
                source_value=value,
                mapped_value=str(item.id),
                status="mapped",
                message="Dictionary item resolved",
            )

        return CashFlowMappingFieldResult(
            target_field=field.target_field,
            mapping_type=field.mapping_type,
            source_path=field.source_path,
            status="error",
            message="Unsupported mapping_type",
        )

    def _extract_path(self, source_payload: dict[str, Any], source_path: str | None):
        if not source_path:
            return False, None
        if not source_path.startswith("$."):
            return False, None
        current: Any = source_payload
        for part in source_path[2:].split("."):
            if isinstance(current, list):
                if not part.isdigit():
                    return False, None
                index = int(part)
                if index >= len(current):
                    return False, None
                current = current[index]
                continue
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]
        return True, current
