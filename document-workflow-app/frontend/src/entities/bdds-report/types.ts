export type BddsGroupPeriod = "day" | "week" | "month" | "quarter" | "year";

export type BddsDiagnosticType =
  | "needs_enrichment"
  | "ignored"
  | "missing_direction"
  | "missing_date"
  | "missing_amount"
  | "missing_cash_flow_item"
  | "missing_currency"
  | "source_changed";

export interface BddsCurrencyRef {
  id: string;
  code: string;
  name?: string | null;
}

export interface BddsCommonFilters {
  date_from: string;
  date_to: string;
  organization_id?: string;
  project_id?: string;
  cash_flow_item_id?: string;
  cash_flow_operation_type_id?: string;
  currency_id?: string;
  group_period?: BddsGroupPeriod;
}

export interface BddsTotalByCurrency {
  currency: BddsCurrencyRef | null;
  inflow_total: number;
  outflow_total: number;
  net_cash_flow: number;
}

export interface BddsSummaryResponse {
  date_from: string;
  date_to: string;
  currency?: BddsCurrencyRef | null;
  inflow_total?: number | null;
  outflow_total?: number | null;
  net_cash_flow?: number | null;
  allocations_count: number;
  inflow_count: number;
  outflow_count: number;
  totals_by_currency?: BddsTotalByCurrency[];
  diagnostics: {
    ignored_allocations_count: number;
    invalid_allocations_count: number;
    needs_enrichment_count: number;
  };
}

export interface BddsCashFlowItemRef {
  id: string;
  code?: string | null;
  name: string;
  direction?: string | null;
}

export interface BddsProjectRef {
  id: string;
  code?: string | null;
  name: string;
}

export interface BddsOrganizationRef {
  id: string;
  name: string;
}

export interface BddsByItemRow {
  cash_flow_item: BddsCashFlowItemRef | null;
  currency: BddsCurrencyRef | null;
  inflow_total: number;
  outflow_total: number;
  net_cash_flow: number;
  allocations_count: number;
}

export interface BddsByProjectRow {
  project: BddsProjectRef | null;
  project_name?: string | null;
  currency: BddsCurrencyRef | null;
  inflow_total: number;
  outflow_total: number;
  net_cash_flow: number;
  allocations_count: number;
}

export interface BddsByOrganizationRow {
  organization: BddsOrganizationRef | null;
  currency: BddsCurrencyRef | null;
  inflow_total: number;
  outflow_total: number;
  net_cash_flow: number;
  allocations_count: number;
}

export interface BddsByPeriodRow {
  period_start: string;
  period_end: string;
  currency: BddsCurrencyRef | null;
  inflow_total: number;
  outflow_total: number;
  net_cash_flow: number;
  allocations_count: number;
}

export interface BddsGroupedResponse<T> {
  items: T[];
  total: number;
}

export interface BddsDiagnosticsQuery extends BddsCommonFilters {
  diagnostic_type?: BddsDiagnosticType;
  limit?: number;
  offset?: number;
}

export interface BddsDiagnosticRow {
  document_id: string;
  source_document_number?: string | null;
  source_document_date?: string | null;
  source_document_type_1c?: string | null;
  diagnostic_type: BddsDiagnosticType;
  allocation_status?: string | null;
  message: string;
}

export interface BddsDiagnosticsResponse {
  items: BddsDiagnosticRow[];
  total: number;
  limit: number;
  offset: number;
}
