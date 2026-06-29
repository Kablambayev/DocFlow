# Payment Registers

Stage 14 introduces grouped outbound sending of approved payment requests.

## Main flow

1. Treasury or accounting user creates a payment register.
2. User adds approved `PaymentRequest` documents.
3. Register is moved from `Draft` to `ReadyToSend`.
4. Register is sent to `1С`.
5. Per-row result is stored both in the register row and in `payment_request_1c_exports`.

## Statuses

- `Draft`
- `ReadyToSend`
- `Sending`
- `PartiallySent`
- `Sent`
- `Failed`
- `Cancelled`

## Permissions

- `payment_register.read`
- `payment_register.manage`
- `payment_register.send`

`accounting_admin` receives all three permissions by seed. `admin` keeps full access through `admin.access`.

## Important rules

- only `PaymentRequest` with status `Approved` can be added;
- archived or already successfully exported requests are excluded;
- failed-export requests are available only when explicitly requested;
- active registers block duplicate inclusion of the same payment request;
- successful rows are skipped on resend unless `force=true`.

## Related artifacts

- backend module: `backend/app/modules/payment_registers/`
- migration: `backend/alembic/versions/20260629_0010_payment_registers.py`
- tests: `backend/tests/test_payment_registers.py`
- frontend pages:
  - `frontend/src/pages/payment-registers/PaymentRegistersPage.tsx`
  - `frontend/src/pages/payment-registers/PaymentRegisterDetailPage.tsx`
