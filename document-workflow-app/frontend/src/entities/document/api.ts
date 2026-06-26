import { apiClient } from "../../shared/api/axios";

import type { DocumentItem, DocumentPayload } from "./types";

export const getDocuments = async () => {
  const { data } = await apiClient.get<DocumentItem[]>("/documents");
  return data;
};

export const getDocument = async (id: string) => {
  const { data } = await apiClient.get<DocumentItem>(`/documents/${id}`);
  return data;
};

export const createDocument = async (payload: DocumentPayload) => {
  const { data } = await apiClient.post<DocumentItem>("/documents", payload);
  return data;
};

export const updateDocument = async (id: string, payload: Partial<DocumentPayload>) => {
  const { data } = await apiClient.put<DocumentItem>(`/documents/${id}`, payload);
  return data;
};

export const submitDocument = async (id: string) => {
  const { data } = await apiClient.post<DocumentItem>(`/documents/${id}/submit`);
  return data;
};

export const withdrawDocument = async (id: string) => {
  const { data } = await apiClient.post<DocumentItem>(`/documents/${id}/withdraw`);
  return data;
};
