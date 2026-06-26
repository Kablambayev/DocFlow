import { apiClient } from "../../shared/api/axios";

import type { DocumentFile } from "./types";

export const getDocumentFiles = async (documentId: string) => {
  const { data } = await apiClient.get<DocumentFile[]>(`/documents/${documentId}/files`);
  return data;
};

export const uploadDocumentFile = async (documentId: string, file: File, fieldCode?: string) => {
  const formData = new FormData();
  formData.append("file", file);
  if (fieldCode) {
    formData.append("field_code", fieldCode);
  }
  const { data } = await apiClient.post<DocumentFile>(`/documents/${documentId}/files`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const downloadFileBlob = async (fileId: string) => {
  const response = await apiClient.get<Blob>(`/files/${fileId}/download`, { responseType: "blob" });
  return response.data;
};

export const deleteFile = async (fileId: string) => {
  const { data } = await apiClient.delete<{ status: "deleted" }>(`/files/${fileId}`);
  return data;
};
