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
  | "dictionary"
  | "reference"
  | "file"
  | "table";

export interface DynamicFieldDependency {
  field: string;
  param: string;
}

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
    dictionary?: string;
    valueField?: string;
    labelField?: string;
    searchable?: boolean;
    dependsOn?: DynamicFieldDependency[];
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
