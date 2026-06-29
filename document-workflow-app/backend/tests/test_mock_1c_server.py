from fastapi.testclient import TestClient

from scripts.mock_1c_server import app


def test_mock_health_and_payment_request(monkeypatch):
    monkeypatch.setenv("MOCK_1C_MODE", "success")
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["service"] == "Mock 1C DocFlow HTTP Service"

    missing = client.post("/payment-requests", json={})
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "REQUEST_ID_REQUIRED"

    created = client.post("/payment-requests", json={"request_id": "req-1", "amount": 1500000})
    assert created.status_code == 200
    assert created.json()["status"] == "created"
    assert created.json()["payment_order"]["external_id"] == "mock-1c-payment-order-req-1"
    assert created.json()["payment_order"]["currency_code"] == "KZT"


def test_mock_business_modes(monkeypatch):
    client = TestClient(app)
    for mode, status in (("already_exists", "already_exists"), ("validation_error", "error")):
        monkeypatch.setenv("MOCK_1C_MODE", mode)
        response = client.post("/payment-requests", json={"request_id": "req-2"})
        assert response.status_code == 200
        assert response.json()["status"] == status

    monkeypatch.setenv("MOCK_1C_MODE", "http_500")
    assert client.post("/payment-requests", json={"request_id": "req-3"}).status_code == 500
