from __future__ import annotations

import re
from uuid import UUID

from fastapi import status

from app.core.exceptions import AppError
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.document_types.models import VersionStatus
from app.modules.document_types.repository import DocumentTypeRepository
from app.modules.document_types.schemas import (
    DocumentTypeCreate,
    DocumentTypeFieldRequest,
    DocumentTypeSectionRequest,
    DocumentTypeUpdate,
    DocumentTypeVersionCreate,
    DocumentTypeVersionUpdate,
    SchemaValidationError,
    SchemaValidationResult,
)


CODE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


class DocumentTypeService:
    def __init__(self, repository: DocumentTypeRepository):
        self.repository = repository
        self.audit_service = AuditService(AuditRepository(self.repository.db))

    def list_document_types(self):
        return self.repository.list()

    def list_active_document_types(self):
        return self.repository.list_active_with_published_version()

    def get_document_type(self, item_id: UUID):
        item = self.repository.get(item_id)
        if item is None:
            raise AppError("Document type not found", code="document_type_not_found", status_code=status.HTTP_404_NOT_FOUND)
        return item

    def create_document_type(self, payload: DocumentTypeCreate):
        exists = self.repository.get_by_code(payload.code)
        if exists is not None:
            raise AppError("Document type code already exists", code="document_type_code_exists", status_code=409)
        return self.repository.create(payload)

    def update_document_type(self, item_id: UUID, payload: DocumentTypeUpdate):
        item = self.get_document_type(item_id)
        if payload.code and payload.code != item.code:
            exists = self.repository.get_by_code(payload.code)
            if exists is not None:
                raise AppError("Document type code already exists", code="document_type_code_exists", status_code=409)
        updated = self.repository.update(item, payload)
        self.audit_service.log("document_type", updated.id, "document_type_updated")
        self.repository.db.commit()
        return updated

    def create_document_type_version(self, document_type_id: UUID, payload: DocumentTypeVersionCreate):
        _ = self.get_document_type(document_type_id)
        self._raise_if_schema_invalid(payload.schema_payload)
        version = self.repository.create_version(document_type_id, payload)
        self.audit_service.log("document_type_version", version.id, "document_type_version_created")
        self.repository.db.commit()
        return version

    def update_version(self, version_id: UUID, payload: DocumentTypeVersionUpdate):
        version = self.get_editable_version(version_id)
        schema_json = payload.schema_payload if payload.schema_payload is not None else version.schema_json
        self._raise_if_schema_invalid(schema_json)
        updated = self.repository.update_version_schema(version, schema_json)
        self.audit_service.log("document_type_version", updated.id, "document_type_version_updated")
        self.repository.db.commit()
        return updated

    def publish_version(self, version_id: UUID):
        version = self.repository.get_version(version_id)
        if version is None:
            raise AppError("Document type version not found", code="version_not_found", status_code=404)
        if version.status != VersionStatus.DRAFT:
            raise AppError("Only draft version can be published", code="invalid_version_state", status_code=409)
        self._raise_if_schema_invalid(version.schema_json)
        published = self.repository.publish_version(version)
        self.audit_service.log("document_type_version", published.id, "document_type_version_published")
        self.repository.db.commit()
        return published

    def get_version(self, version_id: UUID):
        version = self.repository.get_version(version_id)
        if version is None:
            raise AppError("Document type version not found", code="version_not_found", status_code=404)
        return version

    def list_versions(self, document_type_id: UUID):
        _ = self.get_document_type(document_type_id)
        return self.repository.list_versions_by_document_type(document_type_id)

    def get_published_version(self, document_type_id: UUID):
        _ = self.get_document_type(document_type_id)
        version = self.repository.get_latest_published_version(document_type_id)
        if version is None:
            raise AppError("Published document type version not found", code="published_version_not_found", status_code=404)
        return version

    def get_editable_version(self, version_id: UUID):
        version = self.get_version(version_id)
        if version.status != VersionStatus.DRAFT:
            raise AppError("Only draft version can be edited", code="invalid_version_state", status_code=409)
        return version

    def add_section(self, version_id: UUID, payload: DocumentTypeSectionRequest):
        version = self.get_editable_version(version_id)
        self._validate_code(payload.code, "section")
        schema_json = self._normalized_schema(version.schema_json)
        if self._find_section(schema_json, payload.code) is not None:
            raise AppError("Section code already exists", code="section_code_exists", status_code=409)
        schema_json["sections"].append(
            {"code": payload.code, "name": payload.name, "sortOrder": payload.sort_order, "fields": []}
        )
        updated = self.repository.update_version_schema(version, self._sort_schema(schema_json))
        self.audit_service.log("document_type_version", updated.id, "document_type_section_added", new_values_json={"code": payload.code})
        self.repository.db.commit()
        return updated

    def update_section(self, version_id: UUID, section_code: str, payload: DocumentTypeSectionRequest):
        version = self.get_editable_version(version_id)
        self._validate_code(payload.code, "section")
        schema_json = self._normalized_schema(version.schema_json)
        section = self._find_section(schema_json, section_code)
        if section is None:
            raise AppError("Section not found", code="section_not_found", status_code=404)
        if payload.code != section_code and self._find_section(schema_json, payload.code) is not None:
            raise AppError("Section code already exists", code="section_code_exists", status_code=409)
        for field in section.get("fields", []):
            field["sectionCode"] = payload.code
        section.update({"code": payload.code, "name": payload.name, "sortOrder": payload.sort_order})
        updated = self.repository.update_version_schema(version, self._sort_schema(schema_json))
        self.audit_service.log("document_type_version", updated.id, "document_type_section_updated", new_values_json={"code": payload.code})
        self.repository.db.commit()
        return updated

    def delete_section(self, version_id: UUID, section_code: str):
        version = self.get_editable_version(version_id)
        schema_json = self._normalized_schema(version.schema_json)
        section = self._find_section(schema_json, section_code)
        if section is None:
            raise AppError("Section not found", code="section_not_found", status_code=404)
        if section.get("fields"):
            raise AppError("Section contains fields", code="section_not_empty", status_code=409)
        schema_json["sections"] = [item for item in schema_json["sections"] if item.get("code") != section_code]
        updated = self.repository.update_version_schema(version, self._sort_schema(schema_json))
        self.audit_service.log("document_type_version", updated.id, "document_type_section_deleted", old_values_json={"code": section_code})
        self.repository.db.commit()
        return updated

    def add_field(self, version_id: UUID, payload: DocumentTypeFieldRequest):
        version = self.get_editable_version(version_id)
        self._validate_code(payload.code, "field")
        schema_json = self._normalized_schema(version.schema_json)
        section = self._find_section(schema_json, payload.section_code)
        if section is None:
            raise AppError("Section not found", code="section_not_found", status_code=404)
        if self._find_field(schema_json, payload.code) is not None:
            raise AppError("Field code already exists", code="field_code_exists", status_code=409)
        section.setdefault("fields", []).append(self._field_payload(payload))
        updated = self.repository.update_version_schema(version, self._sort_schema(schema_json))
        self.audit_service.log("document_type_version", updated.id, "document_type_field_added", new_values_json={"code": payload.code})
        self.repository.db.commit()
        return updated

    def update_field(self, version_id: UUID, field_code: str, payload: DocumentTypeFieldRequest):
        version = self.get_editable_version(version_id)
        self._validate_code(payload.code, "field")
        schema_json = self._normalized_schema(version.schema_json)
        current = self._find_field_with_section(schema_json, field_code)
        if current is None:
            raise AppError("Field not found", code="field_not_found", status_code=404)
        target_section = self._find_section(schema_json, payload.section_code)
        if target_section is None:
            raise AppError("Section not found", code="section_not_found", status_code=404)
        existing = self._find_field(schema_json, payload.code)
        if payload.code != field_code and existing is not None:
            raise AppError("Field code already exists", code="field_code_exists", status_code=409)
        old_section, old_field = current
        old_section["fields"] = [item for item in old_section.get("fields", []) if item.get("code") != field_code]
        target_section.setdefault("fields", []).append(self._field_payload(payload))
        updated = self.repository.update_version_schema(version, self._sort_schema(schema_json))
        self.audit_service.log("document_type_version", updated.id, "document_type_field_updated", new_values_json={"code": payload.code})
        self.repository.db.commit()
        return updated

    def delete_field(self, version_id: UUID, field_code: str):
        version = self.get_editable_version(version_id)
        schema_json = self._normalized_schema(version.schema_json)
        current = self._find_field_with_section(schema_json, field_code)
        if current is None:
            raise AppError("Field not found", code="field_not_found", status_code=404)
        section, _field = current
        section["fields"] = [item for item in section.get("fields", []) if item.get("code") != field_code]
        updated = self.repository.update_version_schema(version, self._sort_schema(schema_json))
        self.audit_service.log("document_type_version", updated.id, "document_type_field_deleted", old_values_json={"code": field_code})
        self.repository.db.commit()
        return updated

    def validate_schema(self, version_id: UUID) -> SchemaValidationResult:
        version = self.get_version(version_id)
        return self._validate_schema(version.schema_json)

    def _raise_if_schema_invalid(self, schema_json: dict) -> None:
        result = self._validate_schema(schema_json)
        if not result.valid:
            raise AppError(
                "Document type schema is invalid",
                code="schema_validation_error",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details=[error.model_dump() for error in result.errors],
            )

    def _validate_schema(self, schema_json: dict) -> SchemaValidationResult:
        errors: list[SchemaValidationError] = []
        schema = self._normalized_schema(schema_json)
        section_codes: set[str] = set()
        field_codes: set[str] = set()
        for section in schema.get("sections", []):
            section_code = section.get("code")
            if not section_code or not isinstance(section_code, str):
                errors.append(SchemaValidationError(field=None, message="Section code is required"))
            elif not CODE_RE.match(section_code):
                errors.append(SchemaValidationError(field=section_code, message="Invalid section code"))
            elif section_code in section_codes:
                errors.append(SchemaValidationError(field=section_code, message="Duplicate section code"))
            else:
                section_codes.add(section_code)
            if not section.get("name"):
                errors.append(SchemaValidationError(field=section_code, message="Section name is required"))
            for field in section.get("fields", []):
                field_code = field.get("code")
                if not field_code or not isinstance(field_code, str):
                    errors.append(SchemaValidationError(field=None, message="Field code is required"))
                elif not CODE_RE.match(field_code):
                    errors.append(SchemaValidationError(field=field_code, message="Invalid field code"))
                elif field_code in field_codes:
                    errors.append(SchemaValidationError(field=field_code, message="Duplicate field code"))
                else:
                    field_codes.add(field_code)
                if not field.get("name"):
                    errors.append(SchemaValidationError(field=field_code, message="Field name is required"))
                if field.get("type") not in DocumentTypeFieldRequest.model_fields["type"].annotation.__args__:
                    errors.append(SchemaValidationError(field=field_code, message="Unsupported field type"))
        return SchemaValidationResult(valid=not errors, errors=errors)

    def _normalized_schema(self, schema_json: dict | None) -> dict:
        sections = []
        for section in (schema_json or {}).get("sections", []):
            fields = []
            for field in section.get("fields", []):
                fields.append(
                    {
                        "code": field.get("code"),
                        "name": field.get("name"),
                        "type": field.get("type", "string"),
                        "required": bool(field.get("required", False)),
                        "readonly": bool(field.get("readonly", False)),
                        "sortOrder": field.get("sortOrder", field.get("sort_order", 10)),
                        "settings": field.get("settings") or {},
                        "validation": field.get("validation") or {},
                    }
                )
            sections.append(
                {
                    "code": section.get("code"),
                    "name": section.get("name"),
                    "sortOrder": section.get("sortOrder", section.get("sort_order", 10)),
                    "fields": fields,
                }
            )
        return {"sections": sections}

    def _sort_schema(self, schema_json: dict) -> dict:
        schema_json["sections"] = sorted(schema_json.get("sections", []), key=lambda item: item.get("sortOrder", 0))
        for section in schema_json["sections"]:
            section["fields"] = sorted(section.get("fields", []), key=lambda item: item.get("sortOrder", 0))
        return schema_json

    def _validate_code(self, code: str, entity: str) -> None:
        if not CODE_RE.match(code):
            raise AppError(f"Invalid {entity} code", code=f"invalid_{entity}_code", status_code=422)

    def _find_section(self, schema_json: dict, section_code: str) -> dict | None:
        return next((section for section in schema_json.get("sections", []) if section.get("code") == section_code), None)

    def _find_field(self, schema_json: dict, field_code: str) -> dict | None:
        found = self._find_field_with_section(schema_json, field_code)
        return found[1] if found is not None else None

    def _find_field_with_section(self, schema_json: dict, field_code: str) -> tuple[dict, dict] | None:
        for section in schema_json.get("sections", []):
            for field in section.get("fields", []):
                if field.get("code") == field_code:
                    return section, field
        return None

    def _field_payload(self, payload: DocumentTypeFieldRequest) -> dict:
        return {
            "code": payload.code,
            "name": payload.name,
            "type": payload.type,
            "required": payload.required,
            "readonly": payload.readonly,
            "sortOrder": payload.sort_order,
            "settings": payload.settings,
            "validation": payload.validation,
        }
