# CashFlowAllocation and BDDS Mapping

`CashFlowAllocation` (`Разноска БДДС`) is a dynamic DocFlow document used as an intermediate business layer between raw 1C money movement documents and the future BDDS report.

Flow:

`1C document -> mapping rule -> CashFlowAllocation -> future BDDS report`

Why BDDS is not built directly from raw 1C documents:
- 1C documents contain source accounting facts, but not always enough management analytics;
- DocFlow needs a place to enrich, normalize, and validate analytics before reporting;
- the report should be based on unified allocations instead of heterogeneous 1C document formats.

1C source documents for inflow:
- `ПлатежноеПоручениеВходящее`
- `ПриходныйКассовыйОрдер`
- `ПлатежныйОрдерПоступлениеДенежныхСредств`

1C source documents for outflow:
- `ПлатежноеПоручениеИсходящее`
- `РасходныйКассовыйОрдер`
- `ПлатежныйОрдерСписаниеДенежныхСредств`

Normalized DocFlow codes:
- `PaymentOrderIncoming`
- `CashReceiptOrder`
- `MoneyReceiptOrder`
- `PaymentOrderOutgoing`
- `CashExpenseOrder`
- `MoneyExpenseOrder`

`CashFlowAllocation` stores:
- source fields from 1C;
- normalized document type and direction;
- core accounting attributes;
- BDDS analytics;
- service fields for mapping results.

Supported mapping types:
- `path`: take value from source JSON by simple path like `$.organization.external_id`;
- `constant`: inject a fixed value into target field;
- `default`: use source value, otherwise fallback to configured default;
- `dictionary_lookup`: resolve business object from DocFlow dictionaries and map it to UUID.

`dictionary_lookup` supports dictionaries:
- `organization`
- `counterparty`
- `contract`
- `currency`
- `project`
- `cash_flow_operation_type`
- `cash_flow_item`

Lookup keys:
- `external_id`
- `code`
- `name`

Simple JSON path format supported by backend:
- `$.field`
- `$.nested.field`
- `$.array.0.field`

Testing a rule:
1. Open `Сопоставление БДДС`.
2. Choose an existing rule or create a new one.
3. Fill mapping fields.
4. Open tab `Тест маппинга`.
5. Paste source JSON.
6. Run test mapping.
7. Inspect `mapped_data`, `missing_required_fields`, and `field_results`.

Sample JSON:

```json
{
  "ref": "1c-guid",
  "number": "000000123",
  "date": "2026-06-29",
  "posted_at": "2026-06-29T10:00:00+05:00",
  "organization": { "external_id": "ORG-001" },
  "counterparty": { "external_id": "CNT-001" },
  "contract": { "external_id": "CTR-ORG1-CNT1-142" },
  "currency": { "external_id": "CUR-KZT" },
  "amount": 1500000,
  "payment_purpose": "Оплата поставщику",
  "comment": "",
  "project": { "code": "ERP" },
  "cash_flow_item": { "external_id": "dds-supplier-payment" }
}
```

`NeedsEnrichment` means the document was mapped, but the minimum required analytics for completed allocation are incomplete. Current backend requires:
- `organization_id`
- `cash_flow_direction`
- `cash_flow_item_id`
- `currency_id`
- `amount`
- `source_document_date`

What remains for future stages:
- import of 1C money movement documents into actual `CashFlowAllocation` documents;
- UI for mass/manual enrichment of missing analytics;
- final BDDS report and reporting filters.
