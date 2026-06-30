import { apiClient } from "../../shared/api/axios";

import type {
  CashFlowAllocationDetail,
  CashFlowAllocationMetrics,
  CashFlowAllocationQueryParams,
  CashFlowAllocationUpdatePayload,
  CashFlowAllocationsResponse,
} from "./types";

export const getCashFlowAllocations = async (params?: CashFlowAllocationQueryParams) => {
  const { data } = await apiClient.get<CashFlowAllocationsResponse>("/cash-flow/allocations", { params });
  return data;
};

export const getCashFlowAllocationMetrics = async () => {
  const { data } = await apiClient.get<CashFlowAllocationMetrics>("/cash-flow/allocations/metrics");
  return data;
};

export const getCashFlowAllocation = async (documentId: string) => {
  const { data } = await apiClient.get<CashFlowAllocationDetail>(`/cash-flow/allocations/${documentId}`);
  return data;
};

export const updateCashFlowAllocation = async (documentId: string, payload: CashFlowAllocationUpdatePayload) => {
  const { data } = await apiClient.put<CashFlowAllocationDetail>(`/cash-flow/allocations/${documentId}`, payload);
  return data;
};

export const completeCashFlowAllocation = async (documentId: string) => {
  const { data } = await apiClient.post<{ item: CashFlowAllocationDetail }>(`/cash-flow/allocations/${documentId}/complete`);
  return data;
};

export const ignoreCashFlowAllocation = async (documentId: string) => {
  const { data } = await apiClient.post<{ item: CashFlowAllocationDetail }>(`/cash-flow/allocations/${documentId}/ignore`);
  return data;
};

export const reopenCashFlowAllocation = async (documentId: string) => {
  const { data } = await apiClient.post<{ item: CashFlowAllocationDetail }>(`/cash-flow/allocations/${documentId}/reopen`);
  return data;
};
