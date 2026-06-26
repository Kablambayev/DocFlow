from __future__ import annotations

from app.core.config import settings


class OneCOutboundClient:
    """HTTP client placeholder for future DocFlow -> 1C export flow."""

    def __init__(self):
        self.base_url = settings.one_c_base_url
        self.username = settings.one_c_username
        self.password = settings.one_c_password
        self.timeout_seconds = settings.one_c_timeout_seconds
        self.enabled = settings.one_c_enabled

    def send_approved_payment_request(self, payload: dict) -> dict:
        """Stage 9.2 - Send approved PaymentRequest to 1C."""
        raise NotImplementedError("Stage 9.2 - Send approved PaymentRequest to 1C.")
