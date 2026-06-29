export interface PaymentRequest1CExport {
  document_id: string;
  status: string;
  sent_at?: string | null;
  sent_by?: string | null;
  one_c_payment_order_external_id?: string | null;
  one_c_payment_order_number?: string | null;
  one_c_payment_order_date?: string | null;
  one_c_payment_order_amount?: number | null;
  one_c_payment_order_currency_code?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface PaymentRequest1CExportNotExported {
  status: "not_exported";
}

export interface PaymentRequest1CSendResult {
  status: string;
  document_id?: string;
  sent_at?: string | null;
  one_c_enabled?: boolean;
  payment_order?: {
    external_id?: string | null;
    number?: string | null;
    date?: string | null;
    amount?: number | null;
    currency_code?: string | null;
  } | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
  } | null;
  export?: PaymentRequest1CExport;
}

export interface OneCDiagnosticsSettings {
  one_c_enabled: boolean;
  base_url_configured: boolean;
  base_url_preview?: string | null;
  payment_request_endpoint: string;
  health_endpoint: string;
  timeout_seconds: number;
  username_configured: boolean;
  password_configured: boolean;
  verify_ssl: boolean;
}

export interface OneCTestConnectionResult {
  status: "ok" | "disabled" | "error" | "warning";
  one_c_enabled: boolean;
  base_url?: string | null;
  health_endpoint?: string | null;
  http_status?: number | null;
  duration_ms?: number | null;
  service?: string | null;
  version?: string | null;
  code?: string | null;
  message?: string | null;
  details?: Record<string, unknown> | null;
}
