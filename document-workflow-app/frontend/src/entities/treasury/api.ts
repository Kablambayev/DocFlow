import { apiClient } from "../../shared/api/axios";

import type { TreasuryMetrics, TreasuryPaymentRequestQueryParams, TreasuryPaymentRequestsResponse } from "./types";

export const getTreasuryPaymentRequests = async (params?: TreasuryPaymentRequestQueryParams) => {
  const { data } = await apiClient.get<TreasuryPaymentRequestsResponse>("/treasury/payment-requests", { params });
  return data;
};

export const getTreasuryPaymentRequestMetrics = async () => {
  const { data } = await apiClient.get<TreasuryMetrics>("/treasury/payment-requests/metrics");
  return data;
};