export interface PaymentRegisterLookupItem {
  id: string;
  name: string;
  code?: string | null;
}

export interface PaymentRegisterDocumentLookupItem extends PaymentRegisterLookupItem {
  number?: string | null;
}

export interface PaymentRegisterRow {
  id: string;
  register_id: string;
  document_id: string;
  row_number: number;
  amount: number;
  payment_purpose?: string | null;
  organization?: PaymentRegisterLookupItem | null;
  counterparty?: PaymentRegisterLookupItem | null;
  contract?: PaymentRegisterDocumentLookupItem | null;
  currency?: PaymentRegisterLookupItem | null;
  project?: PaymentRegisterLookupItem | null;
  expense_item?: PaymentRegisterLookupItem | null;
  document_number?: string | null;
  document_title?: string | null;
  document_date?: string | null;
  approval_status?: string | null;
  export?: {
    status?: string | null;
    export_id?: string | null;
    one_c_payment_order_external_id?: string | null;
    one_c_payment_order_number?: string | null;
    one_c_payment_order_date?: string | null;
    error_code?: string | null;
    error_message?: string | null;
  } | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentRegister {
  id: string;
  number: string;
  date: string;
  status: string;
  organization?: PaymentRegisterLookupItem | null;
  currency?: PaymentRegisterLookupItem | null;
  comment?: string | null;
  created_by?: PaymentRegisterLookupItem | null;
  sent_by?: PaymentRegisterLookupItem | null;
  sent_at?: string | null;
  total_amount: number;
  rows_count: number;
  sent_rows_count: number;
  failed_rows_count: number;
  created_at: string;
  updated_at: string;
}

export interface PaymentRegisterDetail extends PaymentRegister {
  rows: PaymentRegisterRow[];
}

export interface PaymentRegistersResponse {
  items: PaymentRegister[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaymentRegisterQueryParams {
  status?: string;
  date_from?: string;
  date_to?: string;
  organization_id?: string;
  currency_id?: string;
  search?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface PaymentRegisterCreatePayload {
  number?: string;
  date: string;
  organization_id?: string | null;
  currency_id?: string | null;
  comment?: string | null;
}

export interface PaymentRegisterUpdatePayload {
  number?: string;
  date?: string;
  organization_id?: string | null;
  currency_id?: string | null;
  comment?: string | null;
}

export interface AvailablePaymentRequest {
  document_id: string;
  number: string;
  title?: string | null;
  document_date?: string | null;
  approved_at?: string | null;
  organization?: PaymentRegisterLookupItem | null;
  counterparty?: PaymentRegisterLookupItem | null;
  contract?: PaymentRegisterDocumentLookupItem | null;
  currency?: PaymentRegisterLookupItem | null;
  project?: PaymentRegisterLookupItem | null;
  expense_item?: PaymentRegisterLookupItem | null;
  amount?: number | null;
  payment_purpose?: string | null;
  export_status?: string | null;
  export_error_code?: string | null;
  export_error_message?: string | null;
}

export interface AvailablePaymentRequestsResponse {
  items: AvailablePaymentRequest[];
  total: number;
  limit: number;
  offset: number;
}

export interface AvailablePaymentRequestQueryParams {
  organization_id?: string;
  currency_id?: string;
  search?: string;
  include_failed_exports?: boolean;
  limit?: number;
  offset?: number;
}

export interface PaymentRegisterRowsAddResponse {
  payment_register: PaymentRegisterDetail;
  added_count: number;
  skipped_document_ids: string[];
  errors: Array<{ document_id: string; code: string; message: string }>;
}

export interface PaymentRegisterActionResponse {
  payment_register: PaymentRegisterDetail;
}

export interface PaymentRegisterSendResponse {
  payment_register: PaymentRegisterDetail;
  processed_rows_count: number;
  skipped_rows_count: number;
  results: Array<{
    row_id: string;
    document_id: string;
    export_status?: string | null;
    error_code?: string | null;
    error_message?: string | null;
  }>;
}
