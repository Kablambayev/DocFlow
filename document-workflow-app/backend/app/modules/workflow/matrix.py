from __future__ import annotations

from typing import Any

from app.core.exceptions import AppError


class MatrixEngine:
    SYSTEM_FIELDS = {
        "number",
        "document_date",
        "author_id",
        "organization_id",
        "department_id",
        "approval_status",
        "business_status",
    }

    def resolve_route_id(self, document: Any, rules: list[Any]):
        for rule in rules:
            if self.match_rule(document, rule.condition_json):
                return rule.route_id
        raise AppError(
            "No approval route found",
            code="NO_APPROVAL_ROUTE_FOUND",
            status_code=404,
            details={"document_type_id": str(document.document_type_id)},
        )

    def match_rule(self, document: Any, condition_json: dict) -> bool:
        return self._eval_group(document, condition_json)

    def _eval_group(self, document: Any, node: dict) -> bool:
        operator = node.get("operator", "and").lower()
        conditions = node.get("conditions", [])
        results = []
        for cond in conditions:
            if "conditions" in cond:
                results.append(self._eval_group(document, cond))
            else:
                results.append(self._eval_condition(document, cond))
        return all(results) if operator == "and" else any(results)

    def _eval_condition(self, document: Any, cond: dict) -> bool:
        field = cond.get("field")
        op = cond.get("operator")
        value = cond.get("value")
        actual = self._resolve_field(document, field)

        if op == "=":
            return actual == value
        if op == "!=":
            return actual != value
        if op == ">":
            return actual is not None and value is not None and actual > value
        if op == ">=":
            return actual is not None and value is not None and actual >= value
        if op == "<":
            return actual is not None and value is not None and actual < value
        if op == "<=":
            return actual is not None and value is not None and actual <= value
        if op == "in":
            return actual in (value or [])
        if op == "not_in":
            return actual not in (value or [])
        if op == "is_empty":
            return actual in (None, "", [], {})
        if op == "is_not_empty":
            return actual not in (None, "", [], {})

        return False

    def _resolve_field(self, document: Any, field: str):
        if field in self.SYSTEM_FIELDS and hasattr(document, field):
            return getattr(document, field)
        data_json = getattr(document, "data_json", {}) or {}
        return data_json.get(field)
