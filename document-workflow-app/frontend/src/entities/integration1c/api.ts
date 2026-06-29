import { apiClient } from "../../shared/api/axios";

import type {
  PaymentRequest1CExport,
  PaymentRequest1CExportNotExported,
  PaymentRequest1CSendResult,
} from "./types";

export const sendPaymentRequestTo1C = async (documentId: string, force = false) => {
  const { data } = await apiClient.post<PaymentRequest1CSendResult>(`/integration/1c/payment-requests/${documentId}/send`, undefined, {
    params: { force },
  });
  return data;
};

export const getPaymentRequest1CExport = async (documentId: string) => {
  const { data } = await apiClient.get<PaymentRequest1CExport | PaymentRequest1CExportNotExported>(
    `/integration/1c/payment-requests/${documentId}/export`,
  );
  return data;
};