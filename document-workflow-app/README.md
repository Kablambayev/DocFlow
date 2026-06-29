# Document Workflow App

Enterprise-grade web application for electronic document workflow and approvals.

## Project Structure

- `backend/` - FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL
- `frontend/` - React, TypeScript, Vite, Ant Design
- `docker/` - docker assets for next phases
- `docs/` - architecture and process docs

## Backend Run

1. Open terminal in `backend/`
2. Install dependencies:
	- `python -m pip install -r requirements.txt`
3. Create environment file:
	- copy `.env.example` to `.env`
4. Run migration:
	- `alembic upgrade head`
5. Run backend:
	- `uvicorn app.main:app --reload`

Health check:

- `GET http://127.0.0.1:8000/health` -> `{ "status": "ok" }`

Swagger:

- `http://127.0.0.1:8000/docs`

## Frontend Run

1. Open terminal in `frontend/`
2. Install dependencies:
	- `npm install`
3. Run frontend:
	- `npm run dev`

Frontend opens at Vite local URL (for example `http://127.0.0.1:5173/` or next free port).

## Stage 3 UI Flow

The admin UI now supports the main configuration flow without using JSON as the primary input:

1. Open `Admin -> Document types`.
2. Create a document type.
3. Select it, create a draft form version, add sections and fields, preview the form, then publish the version.
4. Open `Admin -> Approval routes`, create a route for the document type, create a route version, add approval steps, then publish it with `X-User-Id`.
5. Open `Admin -> Approval matrix`, create a rule that links the document type to the route. Use `Always true` for a default route or add simple conditions.
6. Open `Documents -> Create document`, select an active document type, fill the generated form, and create the document.
7. Open the document card, submit it for approval, then use `My tasks` with the approver user id to approve or reject the task.

Raw JSON is kept only in debug/advanced panels where useful; normal create/edit flows use forms.

## Stage 3.1 Constructor Hardening

The constructor now supports editing existing configuration:

- Document form versions:
  - edit sections and change `sortOrder`;
  - delete only empty sections;
  - add, edit, delete fields;
  - configure enum options with one value per line;
  - configure money defaults and advanced `settings` / `validation` JSON;
  - preview draft, published, and archived schemas.
- Approval routes:
  - edit route version steps in draft versions;
  - delete steps;
  - published/archived route versions are read-only;
  - route preview is shown as Ant Design `Steps`.
- Approval matrix:
  - create and edit rules through the condition builder;
  - parse existing `condition_json` back into the form;
  - soft delete rules.
- Users:
  - list users;
  - create and edit users;
  - copy user id for temporary `X-User-Id` usage.

Use `Admin -> Users` to create or copy a user id while the project does not yet have full authentication.

## Stage 4.1 RBAC Without Keycloak

RBAC is implemented with a temporary development header:

- every protected API request must include `X-User-Id`;
- `/api/v1/me` returns the current user;
- `/api/v1/me/permissions` returns permission codes for the current user;
- `admin.access` grants access to every permission check;
- document visibility is limited to the author, assigned approvers, or admin.

Run the seed after migrations to create the RBAC baseline:

```bash
cd backend
python.exe -m alembic upgrade head
python.exe scripts/seed_dev.py
```

Seed users:

- `admin@example.com` -> `admin`
- `author@example.com` -> `document_user`
- `approver@example.com` -> `approver`

Seed roles:

- `admin`
- `document_user`
- `approver`
- `document_constructor`
- `workflow_admin`
- `user_admin`

Seed permissions include document, document type, approval route, approval matrix, user, role, permission, task, audit, and `admin.access` permissions.

Backend regression tests:

```bash
cd backend
python.exe -m pytest
```

The tests cover:

- missing `X-User-Id` -> `AUTH_REQUIRED`;
- admin wildcard access;
- author and approver allowed/denied endpoint checks;
- document visibility;
- submit -> task -> approve workflow authorization.

Manual frontend RBAC smoke:

1. Run backend and frontend.
2. Open `http://127.0.0.1:5173`.
3. Select admin in the dev user selector and verify admin sections are visible.
4. Select author and verify admin sections are hidden.
5. Select approver and verify `My tasks` is visible.
6. Open a protected URL directly and verify the 403 state is rendered.

## Stage 5 Files And Attachments

Documents can now have protected file attachments. Files are stored through a `StorageProvider` abstraction; Stage 5 uses local storage, and MinIO/S3 can be added later behind the same provider boundary.

Local storage settings:

```env
FILE_STORAGE_PROVIDER=local
LOCAL_STORAGE_PATH=storage/uploads
MAX_UPLOAD_SIZE_MB=25
ALLOWED_FILE_EXTENSIONS=.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.txt,.zip
```

Local files are stored under:

```text
backend/storage/uploads/documents/{document_id}/{file_id}_{safe_filename}
```

API endpoints:

- `GET /api/v1/documents/{document_id}/files`
- `POST /api/v1/documents/{document_id}/files`
- `GET /api/v1/files/{file_id}/download`
- `DELETE /api/v1/files/{file_id}`

Required permissions:

- `document_file.read` for list/download;
- `document_file.upload` for upload;
- `document_file.delete` for soft delete.

Access is still limited by document visibility: admin, document author, or assigned approver task. Upload/delete are allowed only for `Draft` and `Withdrawn` documents. Author can upload/delete own Draft/Withdrawn document files; admin can do the same through `admin.access`; approver can read/download files for documents where they have a task, but cannot upload or delete.

Swagger upload:

1. Run backend and open `http://127.0.0.1:8000/docs`.
2. Use `POST /api/v1/documents/{document_id}/files`.
3. Send `X-User-Id` header, multipart `file`, and optional `field_code`.

UI upload:

1. Open a document card.
2. Select a dev user with file permissions.
3. Use the `Files` panel to drag and drop files.
4. Download or delete files from the list.

Audit actions:

- `document_file_uploaded`
- `document_file_downloaded`
- `document_file_deleted`

## Stage 6 Comments And Timelines

Document cards now have tabs for `Основное`, `Файлы`, `Комментарии`, `Согласование`, and `История`.

API endpoints:

- `GET /api/v1/documents/{document_id}/comments`
- `POST /api/v1/documents/{document_id}/comments`
- `PUT /api/v1/comments/{comment_id}`
- `DELETE /api/v1/comments/{comment_id}`
- `GET /api/v1/documents/{document_id}/timeline`
- `GET /api/v1/documents/{document_id}/approval-timeline`

Required permissions:

- `document_comment.read`
- `document_comment.create`
- `document_comment.update`
- `document_comment.delete`

General comments can be created by users who can access the document. A user can edit or delete their own general comments; admin can edit or delete any general comment through `admin.access`. Approval comments are created automatically from approve/reject decisions and cannot be edited or deleted through the comments API. Reject requires a non-empty comment.

The `История` tab aggregates audit events and comments. The `Согласование` tab shows the latest approval process grouped by route step, including approver decisions and decision comments.

## Stage 7.1 In-App Notifications

DocFlow now creates in-app notifications synchronously from existing backend services. Email, Telegram, WebSocket, push notifications, background workers, Kafka, Keycloak, and OAuth2/OIDC are intentionally not part of this stage.

API endpoints:

- `GET /api/v1/notifications/my`
- `GET /api/v1/notifications/unread-count`
- `POST /api/v1/notifications/{notification_id}/read`
- `POST /api/v1/notifications/read-all`

Required permissions:

- `notification.read`
- `notification.update`

Seed grants notification permissions to `admin`, `document_user`, and `approver`.

Notification events:

- `approval_task_created`
- `approval_task_cancelled`
- `approval_task_approved`
- `approval_task_rejected`
- `document_submitted`
- `document_approved`
- `document_rejected`
- `document_withdrawn`
- `document_comment_created`
- `document_file_uploaded`

Users can read and update only their own notifications. The `/notifications/my` endpoint never returns another user's notifications, including for admins. The frontend topbar shows a bell badge for unread notifications and a dropdown with recent notifications. Clicking an item marks it as read and opens the related document when `document_id` is available.

Swagger smoke:

1. Run backend and open `http://127.0.0.1:8000/docs`.
2. Send `X-User-Id` for a seeded user.
3. Call `GET /api/v1/notifications/my`.
4. Call `GET /api/v1/notifications/unread-count`.
5. Call `POST /api/v1/notifications/read-all`.

UI smoke:

## Stage 9.2 Outbound 1C Payment Orders

DocFlow now supports outbound HTTP exchange for approved `PaymentRequest` documents:

- `POST /api/v1/integration/1c/payment-requests/{document_id}/send`
- `GET /api/v1/integration/1c/payment-requests/{document_id}/export`

Business rules:

- only `PaymentRequest` can be sent;
- only `Approved` documents can be sent;
- `Draft`, `OnApproval`, `Rejected`, `Withdrawn`, and `Archived` documents are rejected;
- outbound payload includes only business fields, not workflow internals, comments, history, or files.

DocFlow sends the payment request to 1C only as a basis for creating a payment order. There is no separate `PaymentRequest` object in 1C for this integration stage.

Outbound payload uses dictionary mapping from internal UUIDs in `documents.data_json` to business identifiers expected by 1C:

- 1C external IDs: organization, counterparty, contract, currency, expense item;
- local accounting codes: cash flow operation type, project.

Payload example:

```json
{
  "request_id": "uuid документа DocFlow",
  "request_number": "PAY-000001",
  "request_date": "2026-06-26",
  "organization_external_id": "ORG-001",
  "counterparty_external_id": "CNT-001",
  "contract_external_id": "CTR-ORG1-CNT1-142",
  "currency_external_id": "CUR-KZT",
  "expense_item_external_id": "EXP-002",
  "cash_flow_operation_type_code": "supplier_payment",
  "project_code": "MAIN",
  "amount": 1500000,
  "payment_purpose": "Оплата по договору",
  "comment": null,
  "author": {
    "id": "uuid",
    "email": "author@example.com",
    "name": "Author User"
  },
  "approved_at": "2026-06-26T10:00:00+05:00"
}
```

Supported 1C responses:

- `created` -> export status `CreatedIn1C`;
- `already_exists` -> export status `AlreadyExistsIn1C`;
- `error` -> export status `Failed`.

Idempotency:

- DocFlow stores one export row per document in `payment_request_1c_exports`;
- repeated send without `force=true` returns the existing successful export instead of sending again;
- `request_id = document.id` is always sent so 1C can deduplicate payment orders too.

Fake mode:

- `ONE_C_ENABLED=false` disables the real HTTP call;
- the backend returns a fake payment order and persists it as `CreatedIn1C`;
- API responses include `one_c_enabled: false` so the caller can see the transport mode.

New settings:

```env
ONE_C_BASE_URL=http://1c-server/base/hs/docflow
ONE_C_PAYMENT_REQUEST_ENDPOINT=/payment-requests
ONE_C_USERNAME=
ONE_C_PASSWORD=
ONE_C_TIMEOUT_SECONDS=30
ONE_C_ENABLED=false
```

Permissions:

- send: `integration_1c.payment_request.send`
- export read: document visibility plus `document.read` or `accounting.read`

Notifications and audit:

- success notification: `integration_1c_payment_order_created`
- failure notification: `integration_1c_payment_request_failed`
- audit actions:
  - `integration_1c_payment_request_send_started`
  - `integration_1c_payment_request_created`
  - `integration_1c_payment_request_already_exists`
  - `integration_1c_payment_request_failed`

Swagger smoke:

1. Run backend and seed data.
2. Open `http://127.0.0.1:8000/docs`.
3. Send an approved `PaymentRequest` using admin or accounting_admin `X-User-Id`.
4. Read export state using the `GET` export endpoint.

UI smoke:

1. Open an approved `PaymentRequest` card.
2. Open the `1С` tab.
3. Send the document to 1C or fake 1C.
4. Refresh the page and verify payment order data, history event, and notifications.

## Stage 9.2.1 1C Export Visibility

Stage 9.2.1 hardens document visibility for users responsible for 1C export.

Why this is needed:

- `accounting_admin` has `integration_1c.payment_request.send` and must be able to find approved payment requests ready for export;
- the same user must not get blanket access to all foreign documents.

Visibility rules are now:

- `admin.access` -> all documents;
- document author -> own documents;
- approver -> documents where the user has an approval task;
- `integration_1c.payment_request.send` -> only foreign `Approved` documents with `document_type.code = PaymentRequest`.

`accounting_admin` still does not see:

- foreign `Draft` `PaymentRequest`;
- foreign `OnApproval` `PaymentRequest`;
- foreign `Rejected` or `Withdrawn` `PaymentRequest`;
- foreign approved documents of other types.

API verification:

- `GET /api/v1/documents` includes foreign approved `PaymentRequest` for accounting_admin;
- `GET /api/v1/documents/{id}` returns `200` for such a document and `403` for excluded cases;
- `GET /api/v1/integration/1c/payment-requests/{id}/export` respects the same visibility model.

UI verification:

1. Log in as `accounting_admin` in dev mode.
2. Open the documents list and find a foreign approved `PaymentRequest`.
3. Open the card and verify the `1С` tab is available.
4. Verify foreign draft/on-approval/rejected documents are still not visible.

1. Submit a document as `author@example.com`.
2. Switch to `approver@example.com`.
3. Verify the notification badge and dropdown show a new approval task.
4. Click the notification and verify the document card opens.
5. Approve or reject the task.
6. Switch back to `author@example.com`.
7. Verify the result notification appears and can be marked as read.

## Stage 8 Management Accounting Dictionaries (\u0423\u043f\u0440\u0423\u0447\u0435\u0442)

Stage 8 adds a management accounting layer with external dictionaries (read-only source = `1C`) and local dictionaries (editable in DocFlow). No 1C sync infrastructure, Keycloak, OAuth2/OIDC, background workers, or message brokers were added in this stage.

Backend additions:

- new module: `backend/app/modules/accounting/` (`models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`);
- migrations: `20260626_0005_accounting_dictionaries.py` and `20260626_0006_accounting_updated_at_defaults.py`;
- router registration in `app/main.py` under `/api/v1/accounting`;
- dynamic schema `FieldType` supports `dictionary`;
- document validation supports dictionary checks and contract/org/counterparty consistency.

Accounting permissions:

- `accounting.read`;
- `accounting.manage`;
- `accounting.sync`.

Seed adds:

- role `accounting_admin`;
- user `accounting_admin@example.com`;
- source dictionaries: organizations, counterparties, contracts, currencies, expense items;
- local dictionaries: cash flow operation types, projects;
- `PaymentRequest` published schema enrichment with `management_accounting` dictionary fields.

API endpoints:

- `GET /api/v1/accounting/organizations`
- `GET /api/v1/accounting/counterparties`
- `GET /api/v1/accounting/counterparty-contracts` (supports `organization_id` and `counterparty_id` filters)
- `GET /api/v1/accounting/currencies`
- `GET /api/v1/accounting/expense-items`
- `GET|POST|PUT|DELETE /api/v1/accounting/cash-flow-operation-types`
- `GET|POST|PUT|DELETE /api/v1/accounting/projects`

Frontend additions:

- route `/accounting` and menu item `\u0423\u043f\u0440\u0423\u0447\u0435\u0442` (visible with `accounting.read`);
- page `AccountingDictionariesPage` with tabs for all dictionaries and CRUD for local ones;
- `DynamicFormRenderer` supports dictionary fields with remote loading, dependency params (`dependsOn`), and dependent value reset when parent values change.

Backend tests:

- `backend/tests/test_accounting_dictionaries.py`
- `backend/tests/test_dictionary_fields_validation.py`

They cover permission boundaries, list/filter behavior, local CRUD soft-delete, valid dictionary submission, unknown dictionary ids, and contract-org-counterparty mismatch validation.

## Stage 9 HTTP Integration With 1C

Stage 9 implements the inbound HTTP integration flow `1C -> DocFlow` for dictionary import. The integration is synchronous and REST-only.

Not used in Stage 9:

- Kafka
- RabbitMQ
- Celery/RQ
- event bus / background queues

Inbound base path:

- `/api/v1/integration/1c`

Permission model:

- all import endpoints require `accounting.sync`;
- `admin` has access through `admin.access`;
- `accounting_admin` has access through `accounting.sync`.

Inbound endpoints:

- `POST /api/v1/integration/1c/organizations/import`
- `POST /api/v1/integration/1c/counterparties/import`
- `POST /api/v1/integration/1c/currencies/import`
- `POST /api/v1/integration/1c/expense-items/import`
- `POST /api/v1/integration/1c/counterparty-contracts/import`

Import envelope:

```json
{
  "source_system": "1C",
  "items": []
}
```

- `source_system` is optional, default `1C`;
- max batch size: `1000` items;
- if exceeded, API returns `IMPORT_BATCH_TOO_LARGE` with HTTP `422`.

Import result format:

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

Partial success behavior:

- valid rows are imported;
- invalid rows are skipped;
- per-row errors are returned in `errors`;
- HTTP status remains `200` for partial success.

Upsert/idempotency:

- upsert key is `source_system + external_id`;
- repeated import does not create duplicates;
- repeated rows are counted as `updated`.

Counterparty contracts import specifics:

- accepts external references:
  - `organization_external_id`
  - `counterparty_external_id`
  - `currency_external_id` (optional)
- resolves them within the same `source_system`;
- controlled row errors:
  - `ORGANIZATION_NOT_FOUND`
  - `COUNTERPARTY_NOT_FOUND`
  - `CURRENCY_NOT_FOUND`

Audit events are created for each import call:

- `integration_1c_organizations_imported`
- `integration_1c_counterparties_imported`
- `integration_1c_currencies_imported`
- `integration_1c_expense_items_imported`
- `integration_1c_counterparty_contracts_imported`

Future outbound (`DocFlow -> 1C`) is intentionally not implemented in Stage 9. Only skeleton placeholders exist in:

- `backend/app/modules/integration/one_c/outbound_client.py`
- `backend/app/modules/integration/one_c/outbound_service.py`

Stage 9.2 will send only approved `PaymentRequest` data to 1C for payment order creation, without workflow internals.

Stage 9 settings added to backend config (`.env` optional):

```env
ONE_C_BASE_URL=http://1c-server/base/hs/docflow
ONE_C_USERNAME=
ONE_C_PASSWORD=
ONE_C_TIMEOUT_SECONDS=30
ONE_C_ENABLED=false
```

Detailed contracts are documented in:

- `docs/integration-1c-contracts.md`

## Useful Checks

Backend:

```bash
cd backend
python.exe -m alembic upgrade head
python.exe scripts/seed_dev.py
python.exe -m pytest
python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm.cmd run build
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```
