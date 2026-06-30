from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.modules.accounting.router import router as accounting_router
from app.modules.comments.router import router as comments_router
from app.modules.document_types.router import router as document_type_router
from app.modules.document_types.version_router import router as document_type_version_router
from app.modules.documents.router import router as documents_router
from app.modules.cash_flow.allocation_router import router as cash_flow_allocation_router
from app.modules.cash_flow.mapping_router import router as cash_flow_mapping_router
from app.modules.files.router import router as files_router
from app.modules.integration.one_c.inbound_router import router as integration_one_c_router
from app.modules.integration.log_router import router as integration_log_router
from app.modules.integration.one_c.outbound_router import router as integration_one_c_outbound_router
from app.modules.integration.one_c.diagnostics_router import router as integration_one_c_diagnostics_router
from app.modules.notifications.router import router as notifications_router
from app.modules.payment_registers.router import router as payment_registers_router
from app.modules.roles.router import router as roles_router
from app.modules.treasury.router import router as treasury_router
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
fastapi_app.include_router(cash_flow_allocation_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(cash_flow_mapping_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(files_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(comments_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(notifications_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(workflow_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(roles_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(accounting_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(integration_one_c_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(integration_one_c_outbound_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(integration_one_c_diagnostics_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(integration_log_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(treasury_router, prefix=settings.api_v1_prefix)
fastapi_app.include_router(payment_registers_router, prefix=settings.api_v1_prefix)
