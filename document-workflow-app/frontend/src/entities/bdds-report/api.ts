import { apiClient } from "../../shared/api/axios";

import type {
  BddsByItemRow,
  BddsByOrganizationRow,
  BddsByPeriodRow,
  BddsByProjectRow,
  BddsCommonFilters,
  BddsDiagnosticsQuery,
  BddsDiagnosticsResponse,
  BddsGroupedResponse,
  BddsSummaryResponse,
} from "./types";

const baseUrl = "/cash-flow/bdds-report";

export const getBddsSummary = async (filters: BddsCommonFilters) => {
  const { data } = await apiClient.get<BddsSummaryResponse>(`${baseUrl}/summary`, { params: filters });
  return data;
};

export const getBddsByItems = async (filters: BddsCommonFilters) => {
  const { data } = await apiClient.get<BddsGroupedResponse<BddsByItemRow>>(`${baseUrl}/by-items`, { params: filters });
  return data;
};

export const getBddsByProjects = async (filters: BddsCommonFilters) => {
  const { data } = await apiClient.get<BddsGroupedResponse<BddsByProjectRow>>(`${baseUrl}/by-projects`, { params: filters });
  return data;
};

export const getBddsByOrganizations = async (filters: BddsCommonFilters) => {
  const { data } = await apiClient.get<BddsGroupedResponse<BddsByOrganizationRow>>(`${baseUrl}/by-organizations`, { params: filters });
  return data;
};

export const getBddsByPeriods = async (filters: BddsCommonFilters) => {
  const { data } = await apiClient.get<BddsGroupedResponse<BddsByPeriodRow> & { group_period: string }>(`${baseUrl}/by-periods`, {
    params: filters,
  });
  return data;
};

export const getBddsDiagnostics = async (filters: BddsDiagnosticsQuery) => {
  const { data } = await apiClient.get<BddsDiagnosticsResponse>(`${baseUrl}/diagnostics`, { params: filters });
  return data;
};
