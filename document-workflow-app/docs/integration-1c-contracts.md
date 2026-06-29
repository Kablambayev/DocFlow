# DocFlow Stage 9 - 1C HTTP Integration Contracts

## Stage 12 diagnostics contract

- `GET /api/v1/integration/1c/diagnostics/settings` requires `integration_1c.diagnostics.read` and returns only safe flags, endpoints, timeout, SSL mode, and a credential-free URL preview.
- `POST /api/v1/integration/1c/diagnostics/test-connection` requires `integration_1c.diagnostics.run`; real HTTP runs only when enabled.
- Results: `ok`, `warning`, `disabled`, `error`. Codes: `ONE_C_BASE_URL_NOT_CONFIGURED`, `ONE_C_TIMEOUT`, `ONE_C_CONNECTION_ERROR`, `ONE_C_AUTH_ERROR`, `ONE_C_HTTP_ERROR`, `ONE_C_HEALTH_NON_JSON_RESPONSE`.
- Each run creates an outbound `1c_test_connection` log: disabled=`Skipped`, success/warning=`Success`, error=`Failed`.
- Basic Auth credentials and URL userinfo are never returned or logged.

The mock provides `GET /health` and `POST /payment-requests`; see `docs/1c-http-examples.md`.

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

## 12. Stage 9.2.1 - 1C Export Visibility

### 12.1 Why accounting_admin needs extra visibility

`accounting_admin` is responsible for sending approved payment requests to 1C. Without additional visibility, the user can have the send permission but still be unable to find foreign approved requests in the document list or open them by direct link.

### 12.2 What accounting_admin can see

If the user has `integration_1c.payment_request.send`, the user can see:

- foreign documents with `document_type.code = PaymentRequest`;
- only when `document.approval_status = Approved`.

### 12.3 What accounting_admin still cannot see

- foreign `Draft` `PaymentRequest`;
- foreign `OnApproval` `PaymentRequest`;
- foreign `Rejected` or `Withdrawn` `PaymentRequest`;
- foreign approved documents of any other type.

### 12.4 Required permissions

- send to 1C: `integration_1c.payment_request.send`
- read export info: document visibility plus `document.read` or `accounting.read`

### 12.5 API checks

Use:

- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}`
- `POST /api/v1/integration/1c/payment-requests/{document_id}/send`
- `GET /api/v1/integration/1c/payment-requests/{document_id}/export`

Expected behavior:

- accounting_admin receives `200` for foreign approved `PaymentRequest`;
- accounting_admin receives `403` for excluded foreign documents;
- ordinary `document_user` still does not see foreign approved `PaymentRequest` without the export permission;
- admin still sees all documents.

### 12.6 UI checks

1. Approve a `PaymentRequest` as usual.
2. Log in as `accounting_admin`.
3. Verify the document appears in the list.
4. Open the document card.
5. Verify the `1С` tab is available and send works.
6. Verify unrelated foreign drafts and other document types do not appear.

## 13. Stage 10 - Treasury Workspace

### 13.1 Purpose

Treasury users need a dedicated register of approved payment requests instead of opening every document card manually.

The treasury workspace shows:

- approved payment requests ready for export;
- already exported requests;
- requests with failed export;
- created payment orders returned from 1C.

### 13.2 Endpoints

- `GET /api/v1/treasury/payment-requests`
- `GET /api/v1/treasury/payment-requests/metrics`

The treasury page still uses the existing outbound send endpoint:

- `POST /api/v1/integration/1c/payment-requests/{document_id}/send`

### 13.3 Permissions

- registry read: `treasury.payment_request.read`
- send from registry: `integration_1c.payment_request.send`
- accounting dictionaries for filter lists: `accounting.read`

### 13.4 Registry filters

Supported query params:

- `export_status`
- `approval_status`
- `organization_id`
- `counterparty_id`
- `project_id`
- `currency_id`
- `date_from`
- `date_to`
- `amount_from`
- `amount_to`
- `search`
- `limit`
- `offset`
- `sort_by`
- `sort_order`

Supported `export_status` values:

- `not_exported`
- `Pending`
- `Sent`
- `CreatedIn1C`
- `AlreadyExistsIn1C`
- `Failed`

### 13.5 Metrics

Metrics are calculated only for approved `PaymentRequest` documents:

- `ready_to_send`: approved requests without export row;
- `created_in_1c`: export status `CreatedIn1C`;
- `already_exists_in_1c`: export status `AlreadyExistsIn1C`;
- `failed`: export status `Failed`.

Amounts are calculated from `documents.data_json.amount`.

### 13.6 UI behavior

The frontend treasury page:

- shows metric cards;
- shows a registry table;
- maps missing export row to `Не отправлено`;
- allows `Отправить в 1С` for `not_exported` and `Failed`;
- allows `Повторить` with `force=true` for `CreatedIn1C` and `AlreadyExistsIn1C`;
- shows an error modal for failed exports.

### 13.7 Fake mode

If `ONE_C_ENABLED=false`, treasury send uses the same fake mode as the document card and produces a fake payment order in registry and metrics after refetch.

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

## 14. Stage 11 - Integration Operations Log

Stage 11 adds a dedicated technical journal for 1C integration operations.

### 14.1 Logged directions and operations

Directions:

- `Inbound`
- `Outbound`

Operation types:

- `1c_import_organizations`
- `1c_import_counterparties`
- `1c_import_currencies`
- `1c_import_expense_items`
- `1c_import_counterparty_contracts`
- `1c_export_payment_request`

### 14.2 Stored fields

Each log record may contain:

- request URL and method;
- masked request headers and request payload;
- response status code, headers, and payload;
- error code, message, and details;
- duration in milliseconds;
- initiator user id;
- related `document_id` when operation is tied to a document;
- `correlation_id`;
- `idempotency_key`.

### 14.3 Masking

Sensitive values are masked recursively for dictionaries and arrays.

Masked key patterns include:

- `authorization`
- `password`
- `token`
- `secret`
- `api_key`
- `apikey`
- `access_token`
- `refresh_token`
- `cookie`
- `set-cookie`

This means:

- `ONE_C_PASSWORD` is never stored in plain text;
- Basic Auth headers are not stored in plain text;
- cookies and tokens are not stored in plain text.

### 14.4 API

- `GET /api/v1/integration/logs`
- `GET /api/v1/integration/logs/{log_id}`
- `POST /api/v1/integration/logs/{log_id}/retry`

Permissions:

- list/detail: `integration.log.read`
- retry outbound export: `integration_1c.payment_request.send`

### 14.5 Retry policy

Retry is supported only for:

- `direction = Outbound`
- `operation_type = 1c_export_payment_request`
- `document_id is not null`

Retry uses the existing outbound send flow with `force=true`.

Inbound imports are not retried through the log API. Unsupported retry returns:

```json
{
  "error": {
    "code": "INTEGRATION_LOG_RETRY_NOT_SUPPORTED",
    "message": "Retry is supported only for outbound PaymentRequest export logs"
  }
}
```

## 15. Stage 11.1 diagnostics and deep links

The list endpoint supports direct document filtering:

```http
GET /api/v1/integration/logs?document_id={document_id}
```

Only operations whose `document_id` equals the supplied UUID are returned. The frontend uses this contract for the Treasury row action:

```text
/integration/logs?document_id={document_id}
```

The journal also initializes `direction`, `operation_type`, and `status` from query parameters. These are diagnostics/navigation additions only; inbound and outbound 1C payload contracts are unchanged.

An inbound item with an empty counterparty `name` is rejected at item level with `VALIDATION_ERROR`. Other valid items in the same batch are processed and the operation log status is `PartialSuccess`. Sensitive values in both valid and rejected raw items continue to be recursively masked.
