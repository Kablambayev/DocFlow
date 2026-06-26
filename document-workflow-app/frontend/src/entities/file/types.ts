export interface DocumentFile {
  id: string;
  document_id: string;
  field_code?: string | null;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: string;
  uploaded_at: string;
}
