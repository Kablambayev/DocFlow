from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.modules.document_types.router import router as document_type_router
from app.modules.document_types.version_router import router as document_type_version_router
from app.modules.documents.router import router as documents_router
from app.modules.users.router import router as users_router
from app.modules.workflow.router import router as workflow_router

fastapi_app = FastAPI(title=settings.app_name)
register_exception_handlers(fastapi_app)

allowed_origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
]

# Keep CORS outermost so error responses (including 500) still include CORS headers.
app = CORSMiddleware(
    app=fastapi_app,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@fastapi_app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


fastapi_app.include_router(users_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(document_type_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(document_type_version_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(documents_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(workflow_router, prefix=settings.api_v1_prefix)
