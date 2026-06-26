export interface WorkflowTask {
  id: string;
  process_id: string;
  document_id: string;
  step_order: number;
  step_name: string;
  approver_id: string;
  status: string;
  due_at: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ApprovalRoute {
  id: string;
  document_type_id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ResolverType = "specific_user" | "role";

export interface ApprovalStep {
  order: number;
  name: string;
  type: "sequential" | "parallel";
  approverResolver: { type: "specific_user"; userId: string } | { type: "role"; roleCode: string };
  decisionPolicy: "all" | "any";
  slaHours?: number | null;
}

export interface ApprovalRouteVersion {
  id: string;
  route_id: string;
  version_number: number;
  status: string;
  route_schema_json: { steps: ApprovalStep[] };
  created_at: string;
  updated_at: string;
  published_at: string | null;
}

export interface MatrixCondition {
  field: string;
  operator: string;
  value?: unknown;
}

export interface MatrixConditionGroup {
  operator: "and" | "or";
  conditions: MatrixCondition[];
}

export interface ApprovalMatrixRule {
  id: string;
  document_type_id: string;
  priority: number;
  name: string;
  condition_json: MatrixConditionGroup;
  route_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
