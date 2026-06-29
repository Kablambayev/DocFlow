# 1C HTTP examples

Replace placeholders with values printed by `python.exe scripts/seed_dev.py`.

## Local mock 1C

```powershell
cd backend
$env:MOCK_1C_MODE = "success"
python.exe scripts/mock_1c_server.py --host 127.0.0.1 --port 8010
```

Modes: `success`, `already_exists`, `validation_error`, `http_500`, `slow_timeout`. `MOCK_1C_DELAY_SECONDS` defaults to 10.

```powershell
$env:ONE_C_ENABLED = "true"
$env:ONE_C_BASE_URL = "http://127.0.0.1:8010"
$env:ONE_C_PAYMENT_REQUEST_ENDPOINT = "/payment-requests"
$env:ONE_C_HEALTH_ENDPOINT = "/health"
$env:ONE_C_CONNECTION_TEST_ENDPOINT = "/health"
$env:ONE_C_TIMEOUT_SECONDS = "5"
$env:ONE_C_VERIFY_SSL = "true"
python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## curl

```bash
curl http://127.0.0.1:8010/health
curl -X POST http://127.0.0.1:8000/api/v1/integration/1c/diagnostics/test-connection ^
  -H "X-User-Id: <accounting_admin_user_id>"
curl -X POST http://127.0.0.1:8000/api/v1/integration/1c/organizations/import ^
  -H "Content-Type: application/json" ^
  -H "X-User-Id: <accounting_admin_user_id>" ^
  -d "{\"source_system\":\"1C\",\"items\":[{\"external_id\":\"org-0001\",\"code\":\"ORG-001\",\"name\":\"Demo organization\"}]}"
curl -X POST http://127.0.0.1:8000/api/v1/integration/1c/payment-requests/<document_id>/send ^
  -H "X-User-Id: <accounting_admin_user_id>"
```

## PowerShell

```powershell
$headers = @{ "X-User-Id" = "<accounting_admin_user_id>" }
Invoke-RestMethod http://127.0.0.1:8010/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/integration/1c/diagnostics/test-connection -Headers $headers
$body = @{ source_system = "1C"; items = @(@{ external_id = "org-0001"; code = "ORG-001"; name = "Demo organization" }) } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/integration/1c/organizations/import -Headers $headers -ContentType "application/json" -Body $body
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/integration/1c/payment-requests/<document_id>/send" -Headers $headers
```

UI: `/integration/1c/diagnostics`. Filtered journal: `/integration/logs?operation_type=1c_test_connection`.
