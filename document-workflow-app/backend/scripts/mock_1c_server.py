from __future__ import annotations

import argparse
import os
import time
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock 1C DocFlow HTTP Service")


def mode() -> str:
    return os.getenv("MOCK_1C_MODE", "success").strip().lower()


@app.get("/health")
def health():
    selected = mode()
    if selected == "http_500":
        return JSONResponse(status_code=500, content={"status": "error", "message": "Mock HTTP 500"})
    if selected == "slow_timeout":
        time.sleep(float(os.getenv("MOCK_1C_DELAY_SECONDS", "10")))
    return {"status": "ok", "service": "Mock 1C DocFlow HTTP Service", "version": "1.0.0"}


@app.post("/payment-requests")
def payment_requests(payload: dict[str, Any]):
    selected = mode()
    if selected == "slow_timeout":
        time.sleep(float(os.getenv("MOCK_1C_DELAY_SECONDS", "10")))
    if selected == "http_500":
        return JSONResponse(status_code=500, content={"status": "error", "error": {"code": "MOCK_HTTP_500", "message": "Mock HTTP 500"}})
    request_id = payload.get("request_id")
    if not request_id:
        return JSONResponse(status_code=422, content={"status": "error", "error": {"code": "REQUEST_ID_REQUIRED", "message": "request_id is required"}})
    if selected == "validation_error":
        return {"status": "error", "error": {"code": "VALIDATION_ERROR", "message": "Mock 1C validation failed"}}
    payment_order = {
        "external_id": f"mock-1c-payment-order-{request_id}",
        "number": "MOCK-000001",
        "date": os.getenv("MOCK_1C_PAYMENT_ORDER_DATE", "2026-06-29"),
        "amount": payload.get("amount", 1500000),
        "currency_code": payload.get("currency_code") or "KZT",
        "organization_external_id": payload.get("organization_external_id", "org-0001"),
        "counterparty_external_id": payload.get("counterparty_external_id", "cnt-0001"),
        "purpose": payload.get("payment_purpose") or "Оплата по договору",
    }
    return {"status": "already_exists" if selected == "already_exists" else "created", "payment_order": payment_order}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mock 1C HTTP service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
