# DocFlow Stage 9 - 1C HTTP Integration Contracts

## 1. Architecture

Stage 9 uses synchronous HTTP integration only.

No brokers or async queue infrastructure is used:

- no Kafka
- no RabbitMQ
- no Celery/RQ
- no event bus
- no background queue

## 2. Integration Flows

### 2.1 Inbound (implemented in Stage 9)

Flow: `1C -> DocFlow`

1C calls DocFlow REST endpoints and imports dictionaries:

- organizations
- counterparties
- currencies
- expense items
- counterparty contracts

### 2.2 Outbound (implemented in Stage 9.2)

Flow: `DocFlow -> 1C`

DocFlow sends only fully approved `PaymentRequest` to 1C so 1C can create or reuse a payment order.

1C does not store a separate `PaymentRequest` business object in this scenario. The DocFlow document is used only as a basis for creating a payment order.

DocFlow must not send workflow internals:

- approval route
- approval tasks
- approval decisions
- comments timeline
- document history
- workflow state/statuses

## 3. Base URL and Auth

Base URL:

`/api/v1/integration/1c`

Current auth mode:

- `X-User-Id` header (dev auth)
- inbound import: `accounting.sync` (or `admin.access`)
- outbound send: `integration_1c.payment_request.send` (or `admin.access`)

## 4. Inbound Import Endpoints

- `POST /api/v1/integration/1c/organizations/import`
- `POST /api/v1/integration/1c/counterparties/import`
- `POST /api/v1/integration/1c/currencies/import`
- `POST /api/v1/integration/1c/expense-items/import`
- `POST /api/v1/integration/1c/counterparty-contracts/import`

## 5. Request Envelope

All import endpoints use one envelope:

```json
{
  "source_system": "1C",
  "items": []
}
```

- `source_system` is optional, default is `1C`
- max batch size is 1000 items

If batch is too large:

```json
{
  "error": {
    "code": "IMPORT_BATCH_TOO_LARGE",
    "message": "Import batch is too large",
    "details": {
      "max_items": 1000
    }
  }
}
```

## 6. Import Response Format

```json
{
  "status": "completed",
  "source_system": "1C",
  "entity": "organizations",
  "received": 10,
  "created": 3,
  "updated": 7,
  "skipped": 0,
  "errors": []
}
```

Item error example:

```json
{
  "index": 2,
  "external_id": "ORG-003",
  "code": "VALIDATION_ERROR",
  "message": "name is required",
  "details": {
    "field": "name"
  }
}
```

HTTP status behavior:

- `200 OK`: full success or partial success
- `422`: invalid envelope/structure or batch too large
- `403`: missing `accounting.sync`
- `401`: missing `X-User-Id`

## 7. Dictionary Payload Examples

### 7.1 Organizations

```json
{
  "source_system": "1C",
  "items": [
    {
      "external_id": "org-0001",
      "code": "ORG-001",
      "name": "ТОО \"DocFlow Kazakhstan\"",
      "full_name": "Товарищество с ограниченной ответственностью \"DocFlow Kazakhstan\"",
      "is_active": true,
      "raw_data": {
        "bin": "123456789012"
      }
    }
  ]
}
```

### 7.2 Counterparties

```json
{
  "source_system": "1C",
  "items": [
    {
      "external_id": "cnt-0001",
      "code": "CNT-001",
      "name": "ТОО \"Alpha Supply\"",
      "full_name": "Товарищество с ограниченной ответственностью \"Alpha Supply\"",
      "bin_iin": "990140000001",
      "is_active": true,
      "raw_data": {}
    }
  ]
}
```

### 7.3 Currencies

```json
{
  "source_system": "1C",
  "items": [
    {
      "external_id": "currency-kzt",
      "code": "KZT",
      "name": "Тенге",
      "full_name": "Казахстанский тенге",
      "numeric_code": "398",
      "is_active": true,
      "raw_data": {}
    }
  ]
}
```

### 7.4 Expense Items

```json
{
  "source_system": "1C",
  "items": [
    {
      "external_id": "exp-001",
      "code": "EXP-001",
      "name": "Аренда",
      "full_name": "Расходы на аренду",
      "is_active": true,
      "raw_data": {
        "parent_external_id": null
      }
    }
  ]
}
```

### 7.5 Counterparty Contracts

```json
{
  "source_system": "1C",
  "items": [
    {
      "external_id": "contract-142-p",
      "organization_external_id": "org-0001",
      "counterparty_external_id": "cnt-0001",
      "currency_external_id": "currency-kzt",
      "code": "142-П",
      "name": "Договор поставки №142-П",
      "number": "142-П",
      "contract_date": "2026-01-15",
      "is_active": true,
      "raw_data": {}
    }
  ]
}
```

Contract references are resolved by external IDs in the same `source_system`:

- `organization_external_id` -> organization
- `counterparty_external_id` -> counterparty
- `currency_external_id` (optional) -> currency

## 8. Partial Success

DocFlow imports valid items and skips invalid ones in the same request.

Example behavior:

- `received = 5`
- `created = 3`
- `skipped = 2`
- `errors` contains per-item details

## 9. Idempotency

Upsert key:

`source_system + external_id`

Repeated import of same payload does not create duplicates:

- first call: `created > 0`, `updated = 0`
- second call: `created = 0`, `updated > 0`

## 10. Recommended Import Order

1. organizations
2. counterparties
3. currencies
4. expense_items
5. counterparty_contracts

## 11. Outbound Contract (Stage 9.2)

### 11.1 Trigger condition

`document_type.code = PaymentRequest` and `document.approval_status = Approved`.

Also rejected for outbound:

- `Draft`
- `OnApproval`
- `Rejected`
- `Withdrawn`
- `Archived`
- any non-`PaymentRequest` document type

### 11.2 What DocFlow sends to 1C

DocFlow sends only business attributes:

- request number/date/id;
- mapped organization/counterparty/contract/currency/expense item identifiers;
- local accounting codes for cash flow operation type and project;
- amount, purpose, optional comment;
- author info;
- calculated `approved_at`.

DocFlow does not send:

- approval status metadata;
- approval route;
- approval tasks;
- approval decisions;
- workflow state;
- comments timeline;
- document history;
- files.

### 11.3 Request payload

```json
{
  "request_id": "uuid документа DocFlow",
  "request_number": "PAY-000001",
  "request_date": "2026-06-26",
  "organization_external_id": "org-0001",
  "counterparty_external_id": "cnt-0001",
  "contract_external_id": "contract-142-p",
  "currency_external_id": "currency-kzt",
  "expense_item_external_id": "exp-001",
  "cash_flow_operation_type_code": "supplier_payment",
  "project_code": "ERP",
  "amount": 1500000,
  "payment_purpose": "Оплата по договору поставки №142-П",
  "comment": "Комментарий автора заявки",
  "author": {
    "id": "uuid",
    "email": "author@example.com",
    "name": "Айгерим Нурланова"
  },
  "approved_at": "2026-06-26T10:00:00+05:00"
}
```

Mapping source is `documents.data_json`:

- `organization_id`
- `counterparty_id`
- `contract_id`
- `currency_id`
- `expense_item_id`
- `cash_flow_operation_type_id`
- `project_id`
- `amount`
- `payment_purpose` or current schema field `paymentPurpose`
- `comment` if present

Dictionary mapping:

- internal UUIDs from `documents.data_json` are resolved to 1C `external_id` for organization, counterparty, contract, currency, and expense item;
- local DocFlow accounting dictionaries use `code` for cash flow operation type and project.

If mapping fails, DocFlow returns:

```json
{
  "error": {
    "code": "EXPORT_MAPPING_ERROR",
    "message": "Cannot map PaymentRequest data to 1C payload",
    "details": {
      "field": "organization_id",
      "reason": "Organization external_id not found"
    }
  }
}
```

### 11.4 Responses from 1C

Created:

```json
{
  "status": "created",
  "payment_order": {
    "external_id": "1c-payment-order-guid",
    "number": "000000123",
    "date": "2026-06-26",
    "amount": 1500000,
    "currency_code": "KZT",
    "organization_external_id": "org-0001",
    "counterparty_external_id": "cnt-0001",
    "purpose": "Оплата по договору поставки №142-П"
  }
}
```

Already exists:

```json
{
  "status": "already_exists",
  "payment_order": {
    "external_id": "1c-payment-order-guid",
    "number": "000000123",
    "date": "2026-06-26",
    "amount": 1500000,
    "currency_code": "KZT"
  }
}
```

Error:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Не найден договор контрагента",
    "details": {
      "contract_external_id": "CTR-ORG1-CNT1-142"
    }
  }
}
```

### 11.5 Idempotency

DocFlow stores one export row per document in `payment_request_1c_exports`.

- repeated send without `force=true` returns the existing successful export;
- `force=true` sends again and updates the same export row;
- DocFlow always sends `request_id = document.id` so 1C can deduplicate payment order creation.

### 11.6 Fake mode

If `ONE_C_ENABLED=false`, DocFlow does not perform a real HTTP call.

Instead it returns a fake `created` payload and persists the result as a successful export. API responses include `one_c_enabled: false`.

### 11.7 Settings

```env
ONE_C_BASE_URL=http://1c-server/base/hs/docflow
ONE_C_PAYMENT_REQUEST_ENDPOINT=/payment-requests
ONE_C_USERNAME=
ONE_C_PASSWORD=
ONE_C_TIMEOUT_SECONDS=30
ONE_C_ENABLED=false
```

Final transport URL:

```text
{ONE_C_BASE_URL}{ONE_C_PAYMENT_REQUEST_ENDPOINT}
```

### 11.8 UI and Swagger verification

UI:

1. Open an approved `PaymentRequest`.
2. Open the `1С` tab in the document card.
3. Send to 1C or fake 1C.
4. Verify payment order data, timeline event, and notifications.

Swagger:

1. `POST /api/v1/integration/1c/payment-requests/{document_id}/send`
2. `GET /api/v1/integration/1c/payment-requests/{document_id}/export`

Error:

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Не найден договор контрагента",
    "details": {
      "contract_external_id": "contract-142-p"
    }
  }
}
```

### 11.4 Future outbound idempotency

DocFlow will send `request_id = document_id`.

1C should treat `request_id` as external idempotency key to avoid duplicate payment orders on retries.

## 12. Future export storage (documentation only)

Planned table (not created in Stage 9): `payment_request_1c_exports`

Planned fields:

- `id uuid primary key`
- `document_id uuid not null`
- `status varchar not null`
- `sent_at timestamptz nullable`
- `sent_by uuid nullable`
- `request_payload jsonb not null default '{}'`
- `response_payload jsonb not null default '{}'`
- `one_c_payment_order_external_id varchar nullable`
- `one_c_payment_order_number varchar nullable`
- `one_c_payment_order_date date nullable`
- `error_code varchar nullable`
- `error_message text nullable`
- `created_at timestamptz not null`
- `updated_at timestamptz nullable`

Planned statuses:

- `Pending`
- `Sent`
- `CreatedIn1C`
- `AlreadyExistsIn1C`
- `Failed`
