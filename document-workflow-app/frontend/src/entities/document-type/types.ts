export type DocumentTypeStatus = "draft" | "published" | "archived" | "Draft" | "Published" | "Archived";

export type FieldType =
  | "string"
  | "text"
  | "integer"
  | "decimal"
  | "money"
  | "date"
  | "datetime"
  | "boolean"
  | "enum"
  | "dictionary"
  | "reference"
  | "file"
  | "table";

export interface DocumentFieldSchema {
  code: string;
  name: string;
  type: FieldType;
  required: boolean;
  readonly?: boolean;
  sortOrder?: number;
  settings?: Record<string, unknown>;
  validation?: Record<string, unknown>;
}

export interface DocumentSectionSchema {
  code: string;
  name: string;
  sortOrder?: number;
  fields: DocumentFieldSchema[];
}

export interface DocumentSchema {
  sections: DocumentSectionSchema[];
}

export interface DocumentType {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentTypeVersion {
  id: string;
  document_type_id: string;
  version_number: number;
  status: DocumentTypeStatus;
  schema_json: DocumentSchema;
  created_at: string;
  updated_at: string;
  published_at: string | null;
}

export interface DocumentTypePayload {
  code: string;
  name: string;
  description?: string | null;
  is_system: boolean;
  is_active: boolean;
}

export interface SectionPayload {
  code: string;
  name: string;
  sortOrder: number;
}

export interface FieldPayload {
  sectionCode: string;
  code: string;
  name: string;
  type: FieldType;
  required: boolean;
  readonly: boolean;
  sortOrder: number;
  settings: Record<string, unknown>;
  validation: Record<string, unknown>;
}

export interface SchemaValidationResult {
  valid: boolean;
  errors: Array<{ field: string | null; message: string }>;
}
