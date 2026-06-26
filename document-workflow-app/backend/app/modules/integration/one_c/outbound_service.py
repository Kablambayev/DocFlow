from __future__ import annotations

from app.modules.integration.one_c.outbound_client import OneCOutboundClient


class OneCOutboundService:
    """Service placeholder for future DocFlow -> 1C export orchestration."""

    def __init__(self, client: OneCOutboundClient):
        self.client = client

    def export_approved_payment_request(self, document_id: str) -> dict:
        """Stage 9.2 - Send approved PaymentRequest to 1C."""
        raise NotImplementedError("Stage 9.2 - Send approved PaymentRequest to 1C.")
