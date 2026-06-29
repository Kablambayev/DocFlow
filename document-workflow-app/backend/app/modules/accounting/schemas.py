from __future__ import annotations

from datetime import date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountingDictionaryBaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str | None = None
    name: str
    full_name: str | None = None
    is_active: bool
    source_system: str
    synced_at: datetime | None = None


class AccountingOrganizationRead(AccountingDictionaryBaseRead):
    pass


class AccountingCounterpartyRead(AccountingDictionaryBaseRead):
    pass


class AccountingCurrencyRead(AccountingDictionaryBaseRead):
    pass


class AccountingExpenseItemRead(AccountingDictionaryBaseRead):
    pass


class AccountingCashFlowItemRead(AccountingDictionaryBaseRead):
    direction: str


class AccountingCounterpartyContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    counterparty_id: UUID
    currency_id: UUID | None
    code: str | None
    name: str
    number: str | None
    contract_date: date | None
    is_active: bool
    source_system: str
    synced_at: datetime | None


class CashFlowOperationTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    sort_order: int


class CashFlowOperationTypeCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    sort_order: int = 100


class CashFlowOperationTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AccountingCashFlowItemCreate(BaseModel):
    external_id: str | None = None
    code: str | None = None
    name: str
    full_name: str | None = None
    direction: str = "Both"
    is_active: bool = True
    source_system: str = "1C"
    raw_data: dict = {}


class AccountingCashFlowItemUpdate(BaseModel):
    external_id: str | None = None
    code: str | None = None
    name: str | None = None
    full_name: str | None = None
    direction: str | None = None
    is_active: bool | None = None
    source_system: str | None = None
    raw_data: dict | None = None


class AccountingProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    start_date: date | None
    end_date: date | None
    responsible_user_id: UUID | None


class AccountingProjectCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    responsible_user_id: UUID | None = None


class AccountingProjectUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    responsible_user_id: UUID | None = None
