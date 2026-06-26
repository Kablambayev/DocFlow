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

