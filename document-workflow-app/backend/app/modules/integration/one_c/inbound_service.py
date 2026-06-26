from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.accounting.models import (
    AccountingCounterparty,
    AccountingCounterpartyContract,
    AccountingCurrency,
    AccountingExpenseItem,
    AccountingOrganization,
)
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.integration.one_c.schemas import (
    CounterpartyContractImportItem,
    CounterpartyImportItem,
    CurrencyImportItem,
    ExpenseItemImportItem,
    ImportEnvelope,
    ImportItemError,
    ImportResult,
    OrganizationImportItem,
)

MAX_IMPORT_ITEMS = 1000

ModelT = TypeVar("ModelT", bound=BaseModel)


class OneCInboundService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(AuditRepository(db))

    def import_organizations(self, payload: ImportEnvelope, user_id: UUID) -> ImportResult:
        result = self._init_result(payload, "organizations")
        now = datetime.now(timezone.utc)
        for index, raw_item in enumerate(payload.items):
            parsed = self._validate_item(index, raw_item, OrganizationImportItem, result)
            if parsed is None:
                continue

            existing = self.db.scalar(
                select(AccountingOrganization).where(
                    AccountingOrganization.source_system == payload.source_system,
                    AccountingOrganization.external_id == parsed.external_id,
                )
            )
            if existing is None:
                item = AccountingOrganization(
                    source_system=payload.source_system,
                    external_id=parsed.external_id,
                    code=parsed.code,
                    name=parsed.name,
                    full_name=parsed.full_name,
                    is_active=parsed.is_active,
                    raw_data=parsed.raw_data,
                    synced_at=now,
                )
                self.db.add(item)
                result.created += 1
            else:
                existing.code = parsed.code
                existing.name = parsed.name
                existing.full_name = parsed.full_name
                existing.is_active = parsed.is_active
                existing.raw_data = parsed.raw_data
                existing.synced_at = now
                result.updated += 1

        self._finalize(payload, result, user_id, "integration_1c_organizations_imported")
        return result

    def import_counterparties(self, payload: ImportEnvelope, user_id: UUID) -> ImportResult:
        result = self._init_result(payload, "counterparties")
        now = datetime.now(timezone.utc)
        for index, raw_item in enumerate(payload.items):
            parsed = self._validate_item(index, raw_item, CounterpartyImportItem, result)
            if parsed is None:
                continue

            existing = self.db.scalar(
                select(AccountingCounterparty).where(
                    AccountingCounterparty.source_system == payload.source_system,
                    AccountingCounterparty.external_id == parsed.external_id,
                )
            )
            if existing is None:
                item = AccountingCounterparty(
                    source_system=payload.source_system,
                    external_id=parsed.external_id,
                    code=parsed.code,
                    name=parsed.name,
                    full_name=parsed.full_name,
                    bin_iin=parsed.bin_iin,
                    is_active=parsed.is_active,
                    raw_data=parsed.raw_data,
                    synced_at=now,
                )
                self.db.add(item)
                result.created += 1
            else:
                existing.code = parsed.code
                existing.name = parsed.name
                existing.full_name = parsed.full_name
                existing.bin_iin = parsed.bin_iin
                existing.is_active = parsed.is_active
                existing.raw_data = parsed.raw_data
                existing.synced_at = now
                result.updated += 1

        self._finalize(payload, result, user_id, "integration_1c_counterparties_imported")
        return result

    def import_currencies(self, payload: ImportEnvelope, user_id: UUID) -> ImportResult:
        result = self._init_result(payload, "currencies")
        now = datetime.now(timezone.utc)
        for index, raw_item in enumerate(payload.items):
            parsed = self._validate_item(index, raw_item, CurrencyImportItem, result)
            if parsed is None:
                continue

            existing = self.db.scalar(
                select(AccountingCurrency).where(
                    AccountingCurrency.source_system == payload.source_system,
                    AccountingCurrency.external_id == parsed.external_id,
                )
            )

            code_conflict = self.db.scalar(
                select(AccountingCurrency).where(func.lower(AccountingCurrency.code) == parsed.code.lower())
            )
            if code_conflict is not None and (
                existing is None or code_conflict.id != existing.id
            ):
                self._append_error(
                    result,
                    index=index,
                    external_id=parsed.external_id,
                    code="CURRENCY_CODE_CONFLICT",
                    message="Currency code already exists for another external_id",
                    details={"currency_code": parsed.code},
                )
                continue

            if existing is None:
                item = AccountingCurrency(
                    source_system=payload.source_system,
                    external_id=parsed.external_id,
                    code=parsed.code,
                    name=parsed.name,
                    full_name=parsed.full_name,
                    numeric_code=parsed.numeric_code,
                    is_active=parsed.is_active,
                    raw_data=parsed.raw_data,
                    synced_at=now,
                )
                self.db.add(item)
                result.created += 1
            else:
                existing.code = parsed.code
                existing.name = parsed.name
                existing.full_name = parsed.full_name
                existing.numeric_code = parsed.numeric_code
                existing.is_active = parsed.is_active
                existing.raw_data = parsed.raw_data
                existing.synced_at = now
                result.updated += 1

        self._finalize(payload, result, user_id, "integration_1c_currencies_imported")
        return result

    def import_expense_items(self, payload: ImportEnvelope, user_id: UUID) -> ImportResult:
        result = self._init_result(payload, "expense_items")
        now = datetime.now(timezone.utc)
        for index, raw_item in enumerate(payload.items):
            parsed = self._validate_item(index, raw_item, ExpenseItemImportItem, result)
            if parsed is None:
                continue

            existing = self.db.scalar(
                select(AccountingExpenseItem).where(
                    AccountingExpenseItem.source_system == payload.source_system,
                    AccountingExpenseItem.external_id == parsed.external_id,
                )
            )
            if existing is None:
                item = AccountingExpenseItem(
                    source_system=payload.source_system,
                    external_id=parsed.external_id,
                    code=parsed.code,
                    name=parsed.name,
                    full_name=parsed.full_name,
                    is_active=parsed.is_active,
                    raw_data=parsed.raw_data,
                    synced_at=now,
                )
                self.db.add(item)
                result.created += 1
            else:
                existing.code = parsed.code
                existing.name = parsed.name
                existing.full_name = parsed.full_name
                existing.is_active = parsed.is_active
                existing.raw_data = parsed.raw_data
                existing.synced_at = now
                result.updated += 1

        self._finalize(payload, result, user_id, "integration_1c_expense_items_imported")
        return result

    def import_counterparty_contracts(self, payload: ImportEnvelope, user_id: UUID) -> ImportResult:
        result = self._init_result(payload, "counterparty_contracts")
        now = datetime.now(timezone.utc)
        for index, raw_item in enumerate(payload.items):
            parsed = self._validate_item(index, raw_item, CounterpartyContractImportItem, result)
            if parsed is None:
                continue

            organization = self.db.scalar(
                select(AccountingOrganization).where(
                    AccountingOrganization.source_system == payload.source_system,
                    AccountingOrganization.external_id == parsed.organization_external_id,
                )
            )
            if organization is None:
                self._append_error(
                    result,
                    index=index,
                    external_id=parsed.external_id,
                    code="ORGANIZATION_NOT_FOUND",
                    message="Organization not found by external_id",
                    details={"organization_external_id": parsed.organization_external_id},
                )
                continue

            counterparty = self.db.scalar(
                select(AccountingCounterparty).where(
                    AccountingCounterparty.source_system == payload.source_system,
                    AccountingCounterparty.external_id == parsed.counterparty_external_id,
                )
            )
            if counterparty is None:
                self._append_error(
                    result,
                    index=index,
                    external_id=parsed.external_id,
                    code="COUNTERPARTY_NOT_FOUND",
                    message="Counterparty not found by external_id",
                    details={"counterparty_external_id": parsed.counterparty_external_id},
                )
                continue

            currency = None
            if parsed.currency_external_id:
                currency = self.db.scalar(
                    select(AccountingCurrency).where(
                        AccountingCurrency.source_system == payload.source_system,
                        AccountingCurrency.external_id == parsed.currency_external_id,
                    )
                )
                if currency is None:
                    self._append_error(
                        result,
                        index=index,
                        external_id=parsed.external_id,
                        code="CURRENCY_NOT_FOUND",
                        message="Currency not found by external_id",
                        details={"currency_external_id": parsed.currency_external_id},
                    )
                    continue

            existing = self.db.scalar(
                select(AccountingCounterpartyContract).where(
                    AccountingCounterpartyContract.source_system == payload.source_system,
                    AccountingCounterpartyContract.external_id == parsed.external_id,
                )
            )
            if existing is None:
                item = AccountingCounterpartyContract(
                    source_system=payload.source_system,
                    external_id=parsed.external_id,
                    organization_id=organization.id,
                    counterparty_id=counterparty.id,
                    currency_id=currency.id if currency is not None else None,
                    code=parsed.code,
                    name=parsed.name,
                    number=parsed.number,
                    contract_date=parsed.contract_date,
                    is_active=parsed.is_active,
                    raw_data=parsed.raw_data,
                    synced_at=now,
                )
                self.db.add(item)
                result.created += 1
            else:
                existing.organization_id = organization.id
                existing.counterparty_id = counterparty.id
                existing.currency_id = currency.id if currency is not None else None
                existing.code = parsed.code
                existing.name = parsed.name
                existing.number = parsed.number
                existing.contract_date = parsed.contract_date
                existing.is_active = parsed.is_active
                existing.raw_data = parsed.raw_data
                existing.synced_at = now
                result.updated += 1

        self._finalize(payload, result, user_id, "integration_1c_counterparty_contracts_imported")
        return result

    def _init_result(self, payload: ImportEnvelope, entity: str) -> ImportResult:
        self._validate_batch_size(payload.items)
        return ImportResult(
            source_system=payload.source_system,
            entity=entity,
            received=len(payload.items),
            created=0,
            updated=0,
            skipped=0,
            errors=[],
        )

    def _validate_batch_size(self, items: list[dict[str, Any]]) -> None:
        if len(items) > MAX_IMPORT_ITEMS:
            raise AppError(
                "Import batch is too large",
                code="IMPORT_BATCH_TOO_LARGE",
                status_code=422,
                details={"max_items": MAX_IMPORT_ITEMS},
            )

    def _validate_item(self, index: int, raw_item: dict[str, Any], schema: type[ModelT], result: ImportResult) -> ModelT | None:
        try:
            return schema.model_validate(raw_item)
        except ValidationError as exc:
            first_error = exc.errors()[0]
            field = ".".join(str(part) for part in first_error.get("loc", []))
            message = first_error.get("msg", "Validation error")
            self._append_error(
                result,
                index=index,
                external_id=raw_item.get("external_id") if isinstance(raw_item, dict) else None,
                code="VALIDATION_ERROR",
                message=f"{field} {message}".strip(),
                details={"field": field},
            )
            return None

    def _append_error(
        self,
        result: ImportResult,
        *,
        index: int,
        external_id: str | None,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        result.errors.append(
            ImportItemError(
                index=index,
                external_id=external_id,
                code=code,
                message=message,
                details=details,
            )
        )
        result.skipped += 1

    def _finalize(self, payload: ImportEnvelope, result: ImportResult, user_id: UUID, action: str) -> None:
        self.audit_service.log(
            entity_type="integration_import",
            entity_id=user_id,
            action=action,
            user_id=user_id,
            new_values_json={
                "source_system": payload.source_system,
                "received": result.received,
                "created": result.created,
                "updated": result.updated,
                "skipped": result.skipped,
            },
        )
        self.db.commit()
