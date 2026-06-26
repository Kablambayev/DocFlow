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

## Useful Checks

Backend:

```bash
cd backend
python -m alembic upgrade head
python scripts/seed_dev.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm run build
npm run dev -- --host 127.0.0.1 --port 5173
```
