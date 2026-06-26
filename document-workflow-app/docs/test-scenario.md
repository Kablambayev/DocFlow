# DocFlow Stage 2 Stabilization Scenario

## Stage 3 Admin Scenario

Use the frontend admin pages instead of hand-written JSON:

1. Go to `Admin -> Document types`.
2. Create a document type with `code`, `name`, optional `description`, `is_system`, and `is_active`.
3. Select the type and create a draft version.
4. Add sections and fields through the form builder.
5. Open preview and verify `DynamicFormRenderer` renders the current schema.
6. Publish the draft version.
7. Go to `Admin -> Approval routes`.
8. Create a route for the document type.
9. Create a route version, add at least one step with a specific user approver, save it, and publish it.
10. Go to `Admin -> Approval matrix`.
11. Create an active matrix rule. For a default rule, enable `Always true`.
12. Go to `Documents -> Create document`.
13. Select the active document type, fill the generated form, and create the document.
14. Open the document card, submit it for approval, then approve the generated task from `My tasks`.

The old Swagger scenario below remains valid for regression checks.

## Stage 3.1 Regression Scenario

1. Open `Admin -> Users`, create or edit a user, and copy the user id.
2. Open `Admin -> Document types`.
3. Create a type and draft version if needed.
4. Add a section, edit its name/order, and verify an empty section can be deleted.
5. Add a field, edit its section/name/type/order/settings, and delete it.
6. Add an enum field using one option per line.
7. Open form preview and verify sections/fields are ordered by `sortOrder`.
8. Publish the form version and verify it becomes read-only.
9. Open `Admin -> Approval routes`, create a route version, add/edit/delete steps, and verify preview updates.
10. Publish the route version and verify steps are read-only.
11. Open `Admin -> Approval matrix`, create a rule, edit it, and soft delete it.
12. Open `Documents -> Create document`, create a document from a published form, submit it, and approve the task from `My tasks`.

## Stage 4.1 RBAC Regression Scenario

Stage 4.1 uses temporary development authentication through `X-User-Id`. Do not add Keycloak, JWT, OAuth2/OIDC, Docker, or a new backend framework for this stage.

### Setup

From `backend/`:

```bash
python.exe -m alembic upgrade head
python.exe scripts/seed_dev.py
python.exe -m pytest
```

The seed is idempotent and creates:

- users: `admin@example.com`, `author@example.com`, `approver@example.com`;
- roles: `admin`, `document_user`, `approver`, `document_constructor`, `workflow_admin`, `user_admin`;
- permissions for documents, document types, approval routes, approval matrix, users, roles, permissions, tasks, audit, plus `admin.access`;
- role-permission and user-role assignments.

### Automated Tests

The backend tests live in:

```text
backend/tests/
  __init__.py
  conftest.py
  test_health.py
  test_rbac.py
  test_document_visibility.py
  test_workflow_authorization.py
```

Covered scenarios:

- `GET /health` returns 200;
- missing `X-User-Id` on `/api/v1/me` and `/api/v1/documents` returns 401 with `AUTH_REQUIRED`;
- admin can access `/me`, `/me/permissions`, users, roles, permissions, document types, approval routes, and approval matrix;
- admin permissions include `admin.access`;
- author can access documents and active document types, but cannot access users, roles, routes, or matrix;
- approver can access own tasks and visible documents, but cannot create document types, routes, or matrix rules;
- admin sees seed documents;
- author sees only visible documents;
- direct access to an unrelated foreign document returns `DOCUMENT_ACCESS_DENIED`;
- submit -> task -> approve still works;
- wrong user with approve permission cannot approve another user's task and gets `TASK_ACCESS_DENIED`.

### Manual Frontend Smoke

1. Run backend:

```bash
cd backend
python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

2. Run frontend:

```bash
cd frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

3. Open `http://127.0.0.1:5173`.
4. Select `admin@example.com` in the dev user selector. Admin should see documents, tasks, admin, document types, routes, matrix, users, and roles/permissions.
5. Select `author@example.com`. Author should see document flow pages and should not see admin sections.
6. Select `approver@example.com`. Approver should see `My tasks`.
7. Open a protected admin URL directly as author or approver and verify the 403 state is shown.

### TestClient Check

```bash
python.exe -B -c "from fastapi.testclient import TestClient; from app.main import app; c = TestClient(app); print(c.get('/health').status_code)"
```

Expected output:

```text
200
```

## Stage 5 Files And Attachments Scenario

Stage 5 adds document attachments with local storage. MinIO/S3 is not implemented yet; the backend uses `StorageProvider` and `LocalStorageProvider` so the storage backend can be replaced later without rewriting file business logic.

### Settings

Default backend settings:

```env
FILE_STORAGE_PROVIDER=local
LOCAL_STORAGE_PATH=storage/uploads
MAX_UPLOAD_SIZE_MB=25
ALLOWED_FILE_EXTENSIONS=.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.txt,.zip
```

Local file content is stored under:

```text
backend/storage/uploads/documents/{document_id}/{file_id}_{safe_filename}
```

Original filenames are not used as paths. Downloads are served only through protected API endpoints.

### Permissions

Seed adds:

- `document_file.read`
- `document_file.upload`
- `document_file.delete`

Assignments:

- `admin`: all permissions;
- `document_user`: read/upload/delete document files;
- `approver`: read document files;
- constructor/workflow admin roles do not receive file permissions.

File access rules:

- list/download requires `document_file.read` and document visibility;
- upload requires `document_file.upload`, document visibility, `Draft` or `Withdrawn` status, and document author or admin;
- delete requires `document_file.delete`, `Draft` or `Withdrawn` status, and document author or admin;
- approver can read/download files only for documents where they have an approval task;
- approver cannot upload/delete.

### API Scenario

1. Get or create a Draft document.
2. Upload through Swagger:

```text
POST /api/v1/documents/{document_id}/files
Header: X-User-Id: author_id
multipart:
  file: invoice.pdf
  field_code: invoiceFile
```

3. List:

```text
GET /api/v1/documents/{document_id}/files
```

4. Download:

```text
GET /api/v1/files/{file_id}/download
```

5. Delete:

```text
DELETE /api/v1/files/{file_id}
```

Expected delete response:

```json
{
  "status": "deleted"
}
```

### UI Scenario

1. Run backend and frontend.
2. Open a Draft document card as `author@example.com`.
3. Attach a PDF in the `Files` panel.
4. Verify the file appears in the list.
5. Download it.
6. Delete it.
7. Open an Approved document and verify upload/delete are unavailable.
8. Open a document with an approval task as `approver@example.com` and verify files can be read/downloaded but not uploaded/deleted.

### Automated Tests

Run:

```bash
cd backend
python.exe -m pytest
```

`backend/tests/test_files.py` covers:

- missing `X-User-Id` returns 401;
- author uploads to own Draft document;
- author lists files;
- author downloads files;
- author soft-deletes own Draft file;
- approver reads/downloads after task access;
- approver cannot upload;
- author cannot upload to Approved document;
- extension restriction;
- file size restriction.

## Stage 6 Comments And Timeline Scenario

Stage 6 adds document comments, approval decision comments, a document history timeline, and an approval timeline in the document card.

### Permissions

Seed adds:

- `document_comment.read`
- `document_comment.create`
- `document_comment.update`
- `document_comment.delete`

Assignments:

- `admin`: all permissions;
- `document_user`: read/create/update/delete document comments;
- `approver`: read/create document comments.

Comment access still follows document visibility: admin, document author, or assigned approver task.

### API Scenario

1. Open or create a visible document.
2. Create a general comment:

```text
POST /api/v1/documents/{document_id}/comments
Header: X-User-Id: author_id
```

```json
{
  "comment_text": "Проверить реквизиты"
}
```

3. List document comments:

```text
GET /api/v1/documents/{document_id}/comments
```

4. Update the author's own general comment:

```text
PUT /api/v1/comments/{comment_id}
```

5. Delete the author's own general comment:

```text
DELETE /api/v1/comments/{comment_id}
```

Expected delete response:

```json
{
  "status": "deleted"
}
```

6. Submit a document and reject a task with a required comment:

```text
POST /api/v1/workflow/tasks/{task_id}/reject
```

```json
{
  "comment": "Нужно исправить сумму"
}
```

Expected:

- reject without a comment returns `REJECT_COMMENT_REQUIRED`;
- approve/reject decision comments appear as `approval` comments;
- approval comments cannot be edited or deleted.

### Timeline API

```text
GET /api/v1/documents/{document_id}/timeline
GET /api/v1/documents/{document_id}/approval-timeline
```

Expected:

- document timeline contains audit events and comments sorted by creation time;
- file events are normalized to `file_uploaded` and `file_deleted`;
- approval timeline returns the latest process, steps, tasks, task statuses, and decision comments.

### UI Scenario

1. Run backend and frontend.
2. Open a document card.
3. Use the `Комментарии` tab to add, edit, and delete a general comment.
4. Submit the document and approve or reject it from `Мои задачи`.
5. For reject, leave the comment empty and verify the UI blocks the action.
6. Add a reject comment and verify the task is rejected.
7. Return to the document card.
8. Verify the `Согласование` tab shows steps, approvers, statuses, and decision comments.
9. Verify the `История` tab shows comments and document audit events.

### Automated Tests

Run:

```bash
cd backend
python.exe -m pytest
```

`backend/tests/test_comments.py` and `backend/tests/test_document_timeline.py` cover:

- comment CRUD authorization;
- no access to unrelated document comments;
- approval comments from workflow decisions;
- reject comment requirement;
- approval comments are immutable through the comments API;
- document timeline access and sorting;
- approval timeline shape.

## Stage 7.1 In-App Notifications Scenario

Stage 7.1 adds internal notifications inside DocFlow. Notifications are created synchronously in existing services. Do not add email, Telegram, WebSocket, push notifications, background workers, Celery/RQ, Kafka, Keycloak, OAuth2/OIDC, or Docker for this stage.

### Permissions

Seed adds:

- `notification.read`
- `notification.update`

Assignments:

- `admin`: all permissions;
- `document_user`: read/update own notifications;
- `approver`: read/update own notifications.

Users can access only their own notifications through `/notifications/my`; admin-wide notification browsing is not implemented in Stage 7.1.

### API Endpoints

```text
GET  /api/v1/notifications/my
GET  /api/v1/notifications/unread-count
POST /api/v1/notifications/{notification_id}/read
POST /api/v1/notifications/read-all
```

`GET /notifications/my` accepts:

```text
limit: int = 20
offset: int = 0
is_read: optional bool
```

### Events

Notifications are created for:

- new approval task: `approval_task_created`;
- cancelled approval task: `approval_task_cancelled`;
- approved task: `approval_task_approved`;
- rejected task: `approval_task_rejected`;
- submitted document: `document_submitted`;
- approved document: `document_approved`;
- rejected document: `document_rejected`;
- withdrawn document: `document_withdrawn`;
- new general document comment: `document_comment_created`;
- uploaded file: `document_file_uploaded`.

Self-notifications are skipped where they would only echo the user's own action.

### Swagger Scenario

1. Submit a document as `author@example.com`.
2. Open Swagger and call as `approver@example.com`:

```text
GET /api/v1/notifications/my
GET /api/v1/notifications/unread-count
```

Expected: notification type `approval_task_created` with `document_id` and `task_id`.

3. Mark it read:

```text
POST /api/v1/notifications/{notification_id}/read
```

Expected:

```json
{
  "status": "read"
}
```

4. Mark all read:

```text
POST /api/v1/notifications/read-all
```

Expected:

```json
{
  "status": "read_all",
  "updated_count": 1
}
```

### UI Scenario

1. Run backend and frontend.
2. Select `author@example.com`.
3. Create a Draft document and submit it for approval.
4. Select `approver@example.com`.
5. Verify the bell badge shows unread notifications.
6. Open the dropdown and click the task notification.
7. Verify the document card opens.
8. Approve or reject the task.
9. Select `author@example.com`.
10. Verify the author sees approval/rejection notifications.
11. Use `Прочитать все`.
12. Verify the badge becomes `0`.

### Automated Tests

Run:

```bash
cd backend
python.exe -m pytest
```

`backend/tests/test_notifications.py` covers:

- missing `X-User-Id` returns 401;
- user reads own notifications;
- user cannot mark another user's notification as read;
- unread count;
- mark one as read;
- mark all as read;
- submit creates approver notification;
- approve creates author notifications;
- reject creates author notifications;
- comment creates participant notification;
- file upload creates participant notification.

## Stage 8 Management Accounting Dictionaries Scenario

Stage 8 adds `\u0423\u043f\u0440\u0423\u0447\u0435\u0442` dictionaries and dynamic `dictionary` fields in document schemas. Source dictionaries are read-only snapshots (from `1C` seed data), and local dictionaries are managed in DocFlow.

### Permissions

Seed adds:

- `accounting.read`
- `accounting.manage`
- `accounting.sync`

Assignments:

- `admin`: all permissions;
- `document_user` and `approver`: `accounting.read`;
- `accounting_admin`: `accounting.read`, `accounting.manage`, `accounting.sync`.

### API Endpoints

```text
GET    /api/v1/accounting/organizations
GET    /api/v1/accounting/counterparties
GET    /api/v1/accounting/counterparty-contracts
GET    /api/v1/accounting/currencies
GET    /api/v1/accounting/expense-items
GET    /api/v1/accounting/cash-flow-operation-types
POST   /api/v1/accounting/cash-flow-operation-types
PUT    /api/v1/accounting/cash-flow-operation-types/{id}
DELETE /api/v1/accounting/cash-flow-operation-types/{id}
GET    /api/v1/accounting/projects
POST   /api/v1/accounting/projects
PUT    /api/v1/accounting/projects/{id}
DELETE /api/v1/accounting/projects/{id}
```

`counterparty-contracts` behavior:

- if both `organization_id` and `counterparty_id` are empty, API returns an empty list;
- when filters are provided, contracts are restricted to selected organization+counterparty.

### UI Scenario

1. Run backend and frontend.
2. Login as admin (or any user with `accounting.read`).
3. Open `\u0423\u043f\u0440\u0423\u0447\u0435\u0442` in the sidebar.
4. Verify tabs load source dictionaries: organizations, counterparties, contracts, currencies, expense items.
5. In contracts tab, set organization and counterparty filters and verify only matching contracts are shown.
6. In `\u0412\u0438\u0434\u044b \u043e\u043f\u0435\u0440\u0430\u0446\u0438\u0439 \u0414\u0421`, create, edit, then deactivate a local entry.
7. In `\u041f\u0440\u043e\u0435\u043a\u0442\u044b`, create, edit, then deactivate a local entry.
8. Open `Documents -> Create document` for `PaymentRequest`.
9. Verify `\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0447\u0435\u0441\u043a\u0438\u0439 \u0443\u0447\u0435\u0442` section appears with dictionary fields.
10. Select organization + counterparty and verify contract field becomes enabled and filtered.
11. Change organization or counterparty and verify already selected contract is auto-cleared when no longer valid.
12. Save and submit document; verify workflow and approvals still work.

### Validation Scenario (Swagger)

1. Create `PaymentRequest` with valid dictionary ids from active dictionaries.
2. Repeat with random `project_id` UUID.
3. Verify response is `422` with `DOCUMENT_VALIDATION_ERROR` and field details.
4. Repeat with mismatched `contract_id` for selected organization/counterparty.
5. Verify response is `422` with contract mismatch reason.

### Automated Tests

Run:

```bash
cd backend
python.exe -m pytest
```

Stage 8 coverage includes:

- `backend/tests/test_accounting_dictionaries.py`
- `backend/tests/test_dictionary_fields_validation.py`

Covered checks:

- read/manage permission boundaries;
- contracts filter semantics by organization/counterparty;
- local dictionaries CRUD + soft delete;
- valid dictionary document payload;
- invalid dictionary UUID rejection;
- contract mismatch rejection.

## Stage 9 HTTP Integration With 1C Scenario

Stage 9 implements synchronous inbound HTTP imports from 1C into DocFlow dictionaries. No message brokers or queue workers are used.

### Permissions

All import endpoints require:

- `accounting.sync`

Access matrix:

- `admin`: allowed via `admin.access`;
- `accounting_admin`: allowed;
- `document_user`: forbidden (`403`);
- `approver`: forbidden (`403`).

### Endpoints

```text
POST /api/v1/integration/1c/organizations/import
POST /api/v1/integration/1c/counterparties/import
POST /api/v1/integration/1c/currencies/import
POST /api/v1/integration/1c/expense-items/import
POST /api/v1/integration/1c/counterparty-contracts/import
```

Envelope format:

```json
{
  "source_system": "1C",
  "items": []
}
```

### Recommended import order

1. organizations
2. counterparties
3. currencies
4. expense_items
5. counterparty_contracts

### Swagger inbound smoke

1. Run backend and open `/docs`.
2. Use `X-User-Id` of `accounting_admin@example.com`.
3. Import organizations.
4. Import counterparties.
5. Import currencies.
6. Import expense items.
7. Import counterparty contracts.
8. Verify accounting read endpoints return imported data.
9. Verify contracts filter:

```text
GET /api/v1/accounting/counterparty-contracts?organization_id=...&counterparty_id=...
```

Expected:

- imports are idempotent via `source_system + external_id`;
- partial success returns `200` with row-level `errors`;
- batch > 1000 returns `422` + `IMPORT_BATCH_TOO_LARGE`.

### Future outbound note (Stage 9.2)

Stage 9.2 will implement `DocFlow -> 1C` HTTP export for approved `PaymentRequest` only.

DocFlow will not send workflow internals:

- routes
- tasks
- approval decisions
- comments/timeline/history

1C must create or return a payment order based on request payload.

### Automated tests

Run:

```bash
cd backend
python.exe -m pytest
```

Stage 9 coverage file:

- `backend/tests/test_integration_1c_import.py`

Covered checks:

- missing `X-User-Id` -> `401`;
- missing `accounting.sync` -> `403`;
- admin/accounting_admin access;
- organizations create/reimport/update + validation row errors;
- counterparties create/reimport update;
- currencies create + controlled `CURRENCY_CODE_CONFLICT`;
- expense items create + `is_active=false` updates;
- contracts reference resolution by external ids;
- contracts missing refs -> controlled row errors;
- partial success counters and `errors` array;
- batch-size limit error;
- existing accounting contracts filter still works by internal ids.

## 0. PostgreSQL Check (Windows)

1. Verify PostgreSQL service is running.
2. Ensure backend `.env` has valid credentials:

```env
DATABASE_URL=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=docflow_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your_password>
```

3. If `psql` is not found, add PostgreSQL bin directory to PATH, for example:

```text
C:\Program Files\PostgreSQL\16\bin
```

4. Connect and create DB if needed:

```sql
psql -U postgres -h localhost -p 5432
\l
CREATE DATABASE docflow_db;
\l
```

If auth fails, reset password in pgAdmin for user `postgres` and update `.env`.

## 1. Migration and Run

From `backend/`:

```bash
alembic upgrade head
python scripts/seed_dev.py
uvicorn app.main:app --reload
```

Check:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 2. Validate tables

```sql
psql -U postgres -h localhost -p 5432 -d docflow_db
\dt
```

Expected tables:

- users
- roles
- permissions
- user_roles
- role_permissions
- document_types
- document_type_versions
- document_type_fields
- documents
- approval_routes
- approval_route_versions
- approval_matrix_rules
- approval_processes
- approval_tasks
- approval_decisions
- audit_log
- document_files
- alembic_version

## 3. Swagger end-to-end scenario

Swagger URL: `http://127.0.0.1:8000/docs`

### 3.1 Create author

`POST /api/v1/users`

```json
{
  "email": "author@example.com",
  "full_name": "Author User",
  "is_active": true
}
```

Save `author_id`.

### 3.2 Create approver

`POST /api/v1/users`

```json
{
  "email": "approver@example.com",
  "full_name": "Approver User",
  "is_active": true
}
```

Save `approver_id`.

### 3.3 Create document type

`POST /api/v1/document-types`

```json
{
  "code": "PaymentRequest",
  "name": "Заявка на оплату",
  "description": "Документ для заявки на оплату",
  "is_system": true,
  "is_active": true
}
```

Save `document_type_id`.

### 3.4 Create document type version

`POST /api/v1/document-types/{document_type_id}/versions`

```json
{
  "version_number": 1,
  "schema_json": {
    "sections": [
      {
        "code": "main",
        "name": "Основные данные",
        "fields": [
          {
            "code": "amount",
            "name": "Сумма",
            "type": "money",
            "required": true
          },
          {
            "code": "currency",
            "name": "Валюта",
            "type": "string",
            "required": true
          },
          {
            "code": "paymentPurpose",
            "name": "Назначение платежа",
            "type": "text",
            "required": true
          }
        ]
      }
    ]
  }
}
```

Save `document_type_version_id`.

### 3.5 Publish document type version

`POST /api/v1/document-type-versions/{document_type_version_id}/publish`

Expected status: `published`.

### 3.6 Create approval route

`POST /api/v1/workflow/routes`

```json
{
  "document_type_id": "document_type_id",
  "code": "payment_request_default",
  "name": "Базовый маршрут заявки на оплату",
  "description": "Один согласующий",
  "is_active": true
}
```

Save `route_id`.

### 3.7 Create approval route version

`POST /api/v1/workflow/routes/{route_id}/versions`

```json
{
  "version_number": 1,
  "route_schema_json": {
    "steps": [
      {
        "order": 1,
        "name": "Первый согласующий",
        "type": "sequential",
        "approverResolver": {
          "type": "specific_user",
          "userId": "approver_id"
        },
        "decisionPolicy": "all",
        "slaHours": 24
      }
    ]
  }
}
```

Save `route_version_id`.

### 3.8 Publish approval route version

`POST /api/v1/workflow/route-versions/{route_version_id}/publish`

Header:

- `X-User-Id: author_id`

Expected status: `published`.

### 3.9 Create matrix rule

`POST /api/v1/workflow/matrix-rules`

Header:

- `X-User-Id: author_id`

```json
{
  "document_type_id": "document_type_id",
  "priority": 1,
  "name": "Все заявки на оплату",
  "condition_json": {
    "operator": "and",
    "conditions": []
  },
  "route_id": "route_id",
  "is_active": true
}
```

### 3.10 Create document

`POST /api/v1/documents`

```json
{
  "document_type_id": "document_type_id",
  "document_type_version_id": "document_type_version_id",
  "number": "PAY-000001",
  "document_date": "2026-06-26T10:00:00+05:00",
  "author_id": "author_id",
  "organization_id": null,
  "department_id": null,
  "title": "Заявка на оплату PAY-000001",
  "data_json": {
    "amount": 1500000,
    "currency": "KZT",
    "paymentPurpose": "Оплата по договору"
  }
}
```

Expected: `approval_status = Draft`.
Save `document_id`.

### 3.11 Submit document

`POST /api/v1/documents/{document_id}/submit`

Header:

- `X-User-Id: author_id`

Expected:

- document `approval_status = OnApproval`
- running process exists
- pending task exists

### 3.12 Get approver tasks

`GET /api/v1/workflow/tasks/my`

Header:

- `X-User-Id: approver_id`

Expected: pending task for `document_id`.
Save `task_id`.

### 3.13 Approve task

`POST /api/v1/workflow/tasks/{task_id}/approve`

Header:

- `X-User-Id: approver_id`

```json
{
  "comment": "Согласовано"
}
```

Expected:

- task `status = Approved`
- process `status = Approved`
- document `approval_status = Approved`
- audit events created

## 4. Frontend scenario

1. Run frontend:

```bash
cd frontend
npm run dev
```

2. Open Documents page and create document.
3. In UI fields that ask for `Current User ID` / `X-User-Id`, use `author_id` for submit and `approver_id` for task approval.
4. Verify status transitions in card:

- Draft -> OnApproval -> Approved

