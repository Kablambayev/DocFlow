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

1. Submit a document as `author@example.com`.
2. Switch to `approver@example.com`.
3. Verify the notification badge and dropdown show a new approval task.
4. Click the notification and verify the document card opens.
5. Approve or reject the task.
6. Switch back to `author@example.com`.
7. Verify the result notification appears and can be marked as read.

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
