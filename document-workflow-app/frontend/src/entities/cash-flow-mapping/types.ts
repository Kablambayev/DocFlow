export interface CashFlowMappingRuleField {
  id?: string;
  target_field: string;
  mapping_type: string;
  source_path?: string | null;
  constant_value?: Record<string, unknown> | string | number | boolean | null;
  default_value?: Record<string, unknown> | string | number | boolean | null;
  dictionary_type?: string | null;
  lookup_by?: string | null;
  is_required?: boolean;
  transform?: string | null;
  sort_order: number;
}

export interface CashFlowMappingRule {
  id: string;
  name: string;
  source_system: string;
  source_document_type_1c: string;
  source_document_type_code: string;
  cash_flow_direction: string;
  target_document_type_code: string;
  is_active: boolean;
  priority: number;
  description?: string | null;
  fields: CashFlowMappingRuleField[];
}

export interface CashFlowMappingRuleListItem {
  id: string;
  name: string;
  source_system: string;
  source_document_type_1c: string;
  source_document_type_code: string;
  cash_flow_direction: string;
  target_document_type_code: string;
  is_active: boolean;
  priority: number;
  description?: string | null;
  fields_count: number;
}

export interface CashFlowMappingRulePayload {
  name: string;
  source_system: string;
  source_document_type_1c: string;
  source_document_type_code: string;
  cash_flow_direction: string;
  target_document_type_code: string;
  is_active: boolean;
  priority: number;
  description?: string | null;
  fields: CashFlowMappingRuleField[];
}

export interface CashFlowMappingTestResultField {
  target_field: string;
  mapping_type: string;
  source_path?: string | null;
  source_value?: Record<string, unknown> | string | number | boolean | null;
  mapped_value?: Record<string, unknown> | string | number | boolean | null;
  status: string;
  message?: string | null;
}

export interface CashFlowMappingTestResult {
  rule_id: string;
  status: string;
  mapped_data: Record<string, unknown>;
  missing_required_fields: string[];
  field_results: CashFlowMappingTestResultField[];
}

export interface CashFlowMappingListParams {
  source_document_type_1c?: string;
  cash_flow_direction?: string;
  is_active?: boolean;
}
