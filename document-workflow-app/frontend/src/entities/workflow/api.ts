import { apiClient } from "../../shared/api/axios";

import type { ApprovalMatrixRule, ApprovalRoute, ApprovalRouteVersion, MatrixConditionGroup, WorkflowTask } from "./types";

export const getRoutes = async () => {
  const { data } = await apiClient.get<ApprovalRoute[]>("/workflow/routes");
  return data;
};

export const createRoute = async (payload: Omit<ApprovalRoute, "id" | "created_at" | "updated_at">) => {
  const { data } = await apiClient.post<ApprovalRoute>("/workflow/routes", payload);
  return data;
};

export const getRoute = async (id: string) => {
  const { data } = await apiClient.get<ApprovalRoute>(`/workflow/routes/${id}`);
  return data;
};

export const getRouteVersions = async (routeId: string) => {
  const { data } = await apiClient.get<ApprovalRouteVersion[]>(`/workflow/routes/${routeId}/versions`);
  return data;
};

export const createRouteVersion = async (routeId: string, payload: { route_schema_json: { steps: unknown[] } }) => {
  const { data } = await apiClient.post<ApprovalRouteVersion>(`/workflow/routes/${routeId}/versions`, payload);
  return data;
};

export const updateRouteVersion = async (versionId: string, payload: { route_schema_json: { steps: unknown[] } }) => {
  const { data } = await apiClient.put<ApprovalRouteVersion>(`/workflow/route-versions/${versionId}`, payload);
  return data;
};

export const publishRouteVersion = async (versionId: string) => {
  const { data } = await apiClient.post<ApprovalRouteVersion>(`/workflow/route-versions/${versionId}/publish`);
  return data;
};

export const getMatrixRules = async () => {
  const { data } = await apiClient.get<ApprovalMatrixRule[]>("/workflow/matrix-rules");
  return data;
};

export const createMatrixRule = async (payload: {
  document_type_id: string;
  priority: number;
  name: string;
  condition_json: MatrixConditionGroup;
  route_id: string;
  is_active: boolean;
}) => {
  const { data } = await apiClient.post<ApprovalMatrixRule>("/workflow/matrix-rules", payload);
  return data;
};

export const updateMatrixRule = async (id: string, payload: Partial<ApprovalMatrixRule>) => {
  const { data } = await apiClient.put<ApprovalMatrixRule>(`/workflow/matrix-rules/${id}`, payload);
  return data;
};

export const deleteMatrixRule = async (id: string) => {
  const { data } = await apiClient.delete<ApprovalMatrixRule>(`/workflow/matrix-rules/${id}`);
  return data;
};

export const getMyTasks = async () => {
  const { data } = await apiClient.get<WorkflowTask[]>("/workflow/tasks/my");
  return data;
};

export const approveTask = async (id: string, payload: { comment: string | null }) => {
  const { data } = await apiClient.post<WorkflowTask>(`/workflow/tasks/${id}/approve`, payload);
  return data;
};

export const rejectTask = async (id: string, payload: { comment: string | null }) => {
  const { data } = await apiClient.post<WorkflowTask>(`/workflow/tasks/${id}/reject`, payload);
  return data;
};
