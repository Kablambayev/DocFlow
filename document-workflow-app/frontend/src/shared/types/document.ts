export type DynamicFieldType =
  | "string"
  | "text"
  | "integer"
  | "decimal"
  | "money"
  | "date"
  | "datetime"
  | "boolean"
  | "enum"
  | "reference"
  | "file"
  | "table";

export interface DynamicFieldSchema {
  code: string;
  name: string;
  type: DynamicFieldType;
  required?: boolean;
  readonly?: boolean;
  sortOrder?: number;
  settings?: {
    options?: Array<{ label: string; value: string | number } | string>;
    precision?: number;
    min?: number;
    max?: number;
  };
  validation?: Record<string, unknown>;
}

export interface DynamicSectionSchema {
  code: string;
  name: string;
  sortOrder?: number;
  fields: DynamicFieldSchema[];
}

export interface DynamicFormSchema {
  sections: DynamicSectionSchema[];
}
