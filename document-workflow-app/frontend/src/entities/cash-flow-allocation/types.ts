export type CashFlowAllocationStatus = "NeedsEnrichment" | "Completed" | "Ignored" | "Draft";
export type CashFlowDirection = "Inflow" | "Outflow";

export interface CashFlowAllocationLookupItem {
  id: string;
  name: string;
  code?: string | null;
}

export interface CashFlowAllocationListItem {
  document_id: string;
  source_document_number?: string | null;
  source_document_date?: string | null;
  source_document_type_1c?: string | null;
  cash_flow_direction?: CashFlowDirection | null;
  organization?: CashFlowAllocationLookupItem | null;
  counterparty?: CashFlowAllocationLookupItem | null;
  project?: CashFlowAllocationLookupItem | null;
  cash_flow_item?: CashFlowAllocationLookupItem | null;
  currency?: CashFlowAllocationLookupItem | null;
  amount?: number | null;
  payment_purpose?: string | null;
  allocation_status: CashFlowAllocationStatus;
  missing_required_fields?: string[];
  source_changed?: boolean;
}

export interface CashFlowAllocationsResponse {
  items: CashFlowAllocationListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface CashFlowAllocationMetrics {
  needs_enrichment: number;
  completed: number;
  ignored: number;
  source_changed: number;
}

export interface CashFlowAllocationDetail {
  document_id: string;
  document_number: string;
  document_date: string;
  title: string;
  source_system?: string | null;
  source_document_external_id?: string | null;
  source_document_type?: string | null;
  source_document_type_1c?: string | null;
  source_document_number?: string | null;
  source_document_date?: string | null;
  source_document_posted_at?: string | null;
  source_document_amount?: number | null;
  source_document_currency?: CashFlowAllocationLookupItem | null;
  source_document_purpose?: string | null;
  source_document_comment?: string | null;
  cash_flow_direction?: CashFlowDirection | null;
  organization?: CashFlowAllocationLookupItem | null;
  counterparty?: CashFlowAllocationLookupItem | null;
  contract?: CashFlowAllocationLookupItem | null;
  currency?: CashFlowAllocationLookupItem | null;
  amount?: number | null;
  payment_purpose?: string | null;
  cash_flow_item?: CashFlowAllocationLookupItem | null;
  project?: CashFlowAllocationLookupItem | null;
  cash_flow_operation_type?: CashFlowAllocationLookupItem | null;
  management_comment?: string | null;
  allocation_status: CashFlowAllocationStatus;
  missing_required_fields?: string[];
  source_changed?: boolean;
  mapping_rule_id?: string | null;
  mapping_result?: string | null;
  raw_source_payload?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CashFlowAllocationQueryParams {
  allocation_status?: string;
  cash_flow_direction?: CashFlowDirection;
  organization_id?: string;
  counterparty_id?: string;
  project_id?: string;
  cash_flow_item_id?: string;
  currency_id?: string;
  source_changed?: boolean;
  date_from?: string;
  date_to?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface CashFlowAllocationUpdatePayload {
  cash_flow_item_id?: string | null;
  project_id?: string | null;
  cash_flow_operation_type_id?: string | null;
  management_comment?: string | null;
  allocation_status?: CashFlowAllocationStatus | null;
}
