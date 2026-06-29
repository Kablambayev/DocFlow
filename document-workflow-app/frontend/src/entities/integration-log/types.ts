export interface IntegrationLogListItem {
  id: string;
  direction: "Inbound" | "Outbound";
  integration_system: string;
  operation_type: string;
  status: string;
  document_id?: string | null;
  document_number?: string | null;
  initiated_by?: string | null;
  initiated_by_name?: string | null;
  response_status_code?: number | null;
  error_code?: string | null;
  error_message?: string | null;
  duration_ms?: number | null;
  correlation_id?: string | null;
  idempotency_key?: string | null;
  created_at: string;
}

export interface IntegrationLogDetail extends IntegrationLogListItem {
  entity_type?: string | null;
  entity_id?: string | null;
  request_url?: string | null;
  request_method?: string | null;
  request_headers: Record<string, unknown> | null;
  request_payload: Record<string, unknown> | null;
  response_headers: Record<string, unknown> | null;
  response_payload: Record<string, unknown> | null;
  error_details: Record<string, unknown> | null;
  updated_at?: string | null;
}

export interface IntegrationLogsResponse {
  items: IntegrationLogListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface IntegrationLogQueryParams {
  direction?: "Inbound" | "Outbound";
  operation_type?: string;
  status?: string;
  document_id?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  limit?: number;
  offset?: number;
  sort_by?: "created_at" | "duration_ms" | "status" | "operation_type";
  sort_order?: "asc" | "desc";
}
