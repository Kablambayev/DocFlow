import { apiClient } from "../../shared/api/axios";

import type {
  AccountingDictionaryItem,
  AccountingQueryParams,
  CashFlowItemDictionaryItem,
  CashFlowItemPayload,
  CashFlowOperationTypePayload,
  CounterpartyContractItem,
  CounterpartyContractsQueryParams,
  ProjectPayload,
} from "./types";

export const getOrganizations = async (params?: AccountingQueryParams) => {
  const { data } = await apiClient.get<AccountingDictionaryItem[]>("/accounting/organizations", { params });
  return data;
};

export const getCounterparties = async (params?: AccountingQueryParams) => {
  const { data } = await apiClient.get<AccountingDictionaryItem[]>("/accounting/counterparties", { params });
  return data;
};

export const getCounterpartyContracts = async (params?: CounterpartyContractsQueryParams) => {
  const { data } = await apiClient.get<CounterpartyContractItem[]>("/accounting/counterparty-contracts", { params });
  return data;
};

export const getCurrencies = async (params?: AccountingQueryParams) => {
  const { data } = await apiClient.get<AccountingDictionaryItem[]>("/accounting/currencies", { params });
  return data;
};

export const getExpenseItems = async (params?: AccountingQueryParams) => {
  const { data } = await apiClient.get<AccountingDictionaryItem[]>("/accounting/expense-items", { params });
  return data;
};

export const getCashFlowItems = async (params?: AccountingQueryParams) => {
  const { data } = await apiClient.get<CashFlowItemDictionaryItem[]>("/accounting/cash-flow-items", { params });
  return data;
};

export const createCashFlowItem = async (payload: CashFlowItemPayload) => {
  const { data } = await apiClient.post<CashFlowItemDictionaryItem>("/accounting/cash-flow-items", payload);
  return data;
};

export const updateCashFlowItem = async (id: string, payload: Partial<CashFlowItemPayload>) => {
  const { data } = await apiClient.put<CashFlowItemDictionaryItem>(`/accounting/cash-flow-items/${id}`, payload);
  return data;
};

export const getCashFlowOperationTypes = async (params?: AccountingQueryParams) => {
  const { data } = await apiClient.get<AccountingDictionaryItem[]>("/accounting/cash-flow-operation-types", { params });
  return data;
};

export const createCashFlowOperationType = async (payload: CashFlowOperationTypePayload) => {
  const { data } = await apiClient.post<AccountingDictionaryItem>("/accounting/cash-flow-operation-types", payload);
  return data;
};

export const updateCashFlowOperationType = async (id: string, payload: Partial<CashFlowOperationTypePayload>) => {
  const { data } = await apiClient.put<AccountingDictionaryItem>(`/accounting/cash-flow-operation-types/${id}`, payload);
  return data;
};

export const deleteCashFlowOperationType = async (id: string) => {
  const { data } = await apiClient.delete<AccountingDictionaryItem>(`/accounting/cash-flow-operation-types/${id}`);
  return data;
};

export const getProjects = async (params?: AccountingQueryParams) => {
  const { data } = await apiClient.get<AccountingDictionaryItem[]>("/accounting/projects", { params });
  return data;
};

export const createProject = async (payload: ProjectPayload) => {
  const { data } = await apiClient.post<AccountingDictionaryItem>("/accounting/projects", payload);
  return data;
};

export const updateProject = async (id: string, payload: Partial<ProjectPayload>) => {
  const { data } = await apiClient.put<AccountingDictionaryItem>(`/accounting/projects/${id}`, payload);
  return data;
};

export const deleteProject = async (id: string) => {
  const { data } = await apiClient.delete<AccountingDictionaryItem>(`/accounting/projects/${id}`);
  return data;
};
