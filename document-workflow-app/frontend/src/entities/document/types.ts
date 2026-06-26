export interface DocumentItem {
  id: string;
  document_type_id: string;
  document_type_version_id: string;
  number: string;
  document_date: string;
  author_id: string;
  organization_id: string | null;
  department_id: string | null;
  approval_status: string;
  business_status: string | null;
  title: string;
  data_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentPayload {
  document_type_id: string;
  document_type_version_id: string;
  number: string;
  document_date: string;
  author_id: string;
  organization_id?: string | null;
  department_id?: string | null;
  title: string;
  data_json: Record<string, unknown>;
}
