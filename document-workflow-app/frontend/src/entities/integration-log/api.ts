import { apiClient } from "../../shared/api/axios";

import type { IntegrationLogDetail, IntegrationLogQueryParams, IntegrationLogsResponse } from "./types";

export const getIntegrationLogs = async (params?: IntegrationLogQueryParams) => {
  const { data } = await apiClient.get<IntegrationLogsResponse>("/integration/logs", { params });
  return data;
};

export const getIntegrationLogDetail = async (logId: string) => {
  const { data } = await apiClient.get<IntegrationLogDetail>(`/integration/logs/${logId}`);
  return data;
};

export const retryIntegrationLog = async (logId: string) => {
  const { data } = await apiClient.post(`/integration/logs/${logId}/retry`);
  return data;
};
