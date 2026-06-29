from __future__ import annotations

from datetime import date as DateType
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.modules.integration.one_c.payment_export_models import PaymentRequest1CExport
from app.modules.integration.one_c.payment_export_schemas import (
    ExportErrorInfo,
    PaymentOrderInfo,
    PaymentRequest1CExportRead,
    PaymentRequest1CExportStatusResponse,
    PaymentRequest1CSendResponse,
)


class PaymentRequest1CExportPresenter:
    def get_export_response(self, export: PaymentRequest1CExport | None):
        if export is None:
            return PaymentRequest1CExportStatusResponse(status="not_exported")
        return PaymentRequest1CExportRead.model_validate(export)

    def build_send_response(
        self,
        *,
        export: PaymentRequest1CExport,
        one_c_enabled: bool,
    ) -> PaymentRequest1CSendResponse:
        error = None
        if export.error_code or export.error_message:
            error = ExportErrorInfo(code=export.error_code or "EXPORT_FAILED", message=export.error_message or "Export failed")
        return PaymentRequest1CSendResponse(
            status=export.status,
            document_id=export.document_id,
            sent_at=export.sent_at,
            one_c_enabled=one_c_enabled,
            payment_order=self._payment_order_from_export(export),
            error=error,
        )

    def build_fake_response(self, *, document_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        amount = payload.get("amount")
        return {
            "status": "created",
            "payment_order": {
                "external_id": f"fake-1c-payment-order-{document_id}",
                "number": "FAKE-000001",
                "date": str(payload.get("request_date") or DateType.today()),
                "amount": amount,
                "currency_code": payload.get("currency_external_id", "KZT").split("-")[-1].upper()
                if payload.get("currency_external_id")
                else "KZT",
                "organization_external_id": payload.get("organization_external_id"),
                "counterparty_external_id": payload.get("counterparty_external_id"),
                "purpose": payload.get("payment_purpose"),
            },
            "one_c_enabled": False,
        }

    def normalize_payment_order(self, payment_order: dict[str, Any] | None) -> dict[str, Any]:
        if not payment_order:
            return {}
        normalized: dict[str, Any] = dict(payment_order)
        if normalized.get("date") and isinstance(normalized["date"], str):
            normalized["date"] = DateType.fromisoformat(normalized["date"])
        if normalized.get("amount") is not None and not isinstance(normalized["amount"], Decimal):
            normalized["amount"] = Decimal(str(normalized["amount"]))
        return normalized

    def _payment_order_from_export(self, export: PaymentRequest1CExport) -> PaymentOrderInfo | None:
        if not any(
            [
                export.one_c_payment_order_external_id,
                export.one_c_payment_order_number,
                export.one_c_payment_order_date,
                export.one_c_payment_order_amount,
                export.one_c_payment_order_currency_code,
            ]
        ):
            return None
        return PaymentOrderInfo(
            external_id=export.one_c_payment_order_external_id,
            number=export.one_c_payment_order_number,
            date=export.one_c_payment_order_date,
            amount=export.one_c_payment_order_amount,
            currency_code=export.one_c_payment_order_currency_code,
        )