import { apiClient } from "../../shared/api/axios";

import type {
  AvailablePaymentRequestQueryParams,
  AvailablePaymentRequestsResponse,
  PaymentRegisterActionResponse,
  PaymentRegisterCreatePayload,
  PaymentRegisterDetail,
  PaymentRegisterQueryParams,
  PaymentRegisterRowsAddResponse,
  PaymentRegisterSendResponse,
  PaymentRegisterUpdatePayload,
  PaymentRegistersResponse,
} from "./types";

export const getPaymentRegisters = async (params?: PaymentRegisterQueryParams) => {
  const { data } = await apiClient.get<PaymentRegistersResponse>("/payment-registers", { params });
  return data;
};

export const createPaymentRegister = async (payload: PaymentRegisterCreatePayload) => {
  const { data } = await apiClient.post<PaymentRegisterDetail>("/payment-registers", payload);
  return data;
};

export const getPaymentRegister = async (registerId: string) => {
  const { data } = await apiClient.get<PaymentRegisterDetail>(`/payment-registers/${registerId}`);
  return data;
};

export const updatePaymentRegister = async (registerId: string, payload: PaymentRegisterUpdatePayload) => {
  const { data } = await apiClient.put<PaymentRegisterDetail>(`/payment-registers/${registerId}`, payload);
  return data;
};

export const deletePaymentRegister = async (registerId: string) => {
  await apiClient.delete(`/payment-registers/${registerId}`);
};

export const getAvailablePaymentRequests = async (params?: AvailablePaymentRequestQueryParams) => {
  const { data } = await apiClient.get<AvailablePaymentRequestsResponse>("/payment-registers/available-payment-requests", { params });
  return data;
};

export const addPaymentRegisterRows = async (registerId: string, documentIds: string[]) => {
  const { data } = await apiClient.post<PaymentRegisterRowsAddResponse>(`/payment-registers/${registerId}/rows`, { document_ids: documentIds });
  return data;
};

export const removePaymentRegisterRow = async (registerId: string, rowId: string) => {
  const { data } = await apiClient.delete<PaymentRegisterDetail>(`/payment-registers/${registerId}/rows/${rowId}`);
  return data;
};

export const markPaymentRegisterReady = async (registerId: string) => {
  const { data } = await apiClient.post<PaymentRegisterActionResponse>(`/payment-registers/${registerId}/mark-ready`);
  return data;
};

export const sendPaymentRegisterTo1C = async (registerId: string, force = false) => {
  const { data } = await apiClient.post<PaymentRegisterSendResponse>(`/payment-registers/${registerId}/send-to-1c`, undefined, { params: { force } });
  return data;
};

export const cancelPaymentRegister = async (registerId: string) => {
  const { data } = await apiClient.post<PaymentRegisterActionResponse>(`/payment-registers/${registerId}/cancel`);
  return data;
};
