import { apiClient } from "../../shared/api/axios";

import type {
  CashFlowMappingListParams,
  CashFlowMappingRule,
  CashFlowMappingRuleListItem,
  CashFlowMappingRulePayload,
  CashFlowMappingTestResult,
} from "./types";

export const getCashFlowMappingRules = async (params?: CashFlowMappingListParams) => {
  const { data } = await apiClient.get<CashFlowMappingRuleListItem[]>("/cash-flow/mapping-rules", { params });
  return data;
};

export const getCashFlowMappingRule = async (id: string) => {
  const { data } = await apiClient.get<CashFlowMappingRule>(`/cash-flow/mapping-rules/${id}`);
  return data;
};

export const createCashFlowMappingRule = async (payload: CashFlowMappingRulePayload) => {
  const { data } = await apiClient.post<CashFlowMappingRule>("/cash-flow/mapping-rules", payload);
  return data;
};

export const updateCashFlowMappingRule = async (id: string, payload: Partial<CashFlowMappingRulePayload>) => {
  const { data } = await apiClient.put<CashFlowMappingRule>(`/cash-flow/mapping-rules/${id}`, payload);
  return data;
};

export const deleteCashFlowMappingRule = async (id: string) => {
  await apiClient.delete(`/cash-flow/mapping-rules/${id}`);
};

export const testCashFlowMappingRule = async (id: string, source_payload: Record<string, unknown>) => {
  const { data } = await apiClient.post<CashFlowMappingTestResult>(`/cash-flow/mapping-rules/${id}/test`, { source_payload });
  return data;
};
