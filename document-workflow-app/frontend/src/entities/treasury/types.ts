export interface TreasuryPaymentRequest {
  document_id: string;
  number: string;
  title?: string | null;
  document_date?: string | null;
  approved_at?: string | null;
  approval_status: string;
  organization?: { id: string; name: string } | null;
  counterparty?: { id: string; name: string } | null;
  contract?: { id: string; name: string } | null;
  currency?: { id: string; code: string; name: string } | null;
  project?: { id: string; code?: string | null; name: string } | null;
  expense_item?: { id: string; name: string } | null;
  amount?: number | null;
  payment_purpose?: string | null;
  export?: {
    status: string;
    sent_at?: string | null;
    one_c_payment_order_external_id?: string | null;
    one_c_payment_order_number?: string | null;
    one_c_payment_order_date?: string | null;
    one_c_payment_order_amount?: number | null;
    one_c_payment_order_currency_code?: string | null;
    error_code?: string | null;
    error_message?: string | null;
  } | null;
}

export interface TreasuryPaymentRequestsResponse {
  items: TreasuryPaymentRequest[];
  total: number;
  limit: number;
  offset: number;
}

export interface TreasuryMetrics {
  ready_to_send: number;
  created_in_1c: number;
  already_exists_in_1c: number;
  failed: number;
  total_amount_ready: number;
  total_amount_created_in_1c: number;
}

export interface TreasuryPaymentRequestQueryParams {
  export_status?: string;
  approval_status?: string;
  organization_id?: string;
  counterparty_id?: string;
  project_id?: string;
  currency_id?: string;
  date_from?: string;
  date_to?: string;
  amount_from?: number;
  amount_to?: number;
  search?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}