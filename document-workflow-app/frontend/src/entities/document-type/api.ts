import { apiClient } from "../../shared/api/axios";

import type {
  DocumentType,
  DocumentTypePayload,
  DocumentTypeVersion,
  FieldPayload,
  SchemaValidationResult,
  SectionPayload,
} from "./types";

export const getDocumentTypes = async () => {
  const { data } = await apiClient.get<DocumentType[]>("/document-types");
  return data;
};

export const getActiveDocumentTypes = async () => {
  const { data } = await apiClient.get<DocumentType[]>("/document-types/active");
  return data;
};

export const getDocumentType = async (id: string) => {
  const { data } = await apiClient.get<DocumentType>(`/document-types/${id}`);
  return data;
};

export const createDocumentType = async (payload: DocumentTypePayload) => {
  const { data } = await apiClient.post<DocumentType>("/document-types", payload);
  return data;
};

export const updateDocumentType = async (id: string, payload: Partial<DocumentTypePayload>) => {
  const { data } = await apiClient.put<DocumentType>(`/document-types/${id}`, payload);
  return data;
};

export const getDocumentTypeVersions = async (documentTypeId: string) => {
  const { data } = await apiClient.get<DocumentTypeVersion[]>(`/document-types/${documentTypeId}/versions`);
  return data;
};

export const getDocumentTypeVersion = async (id: string) => {
  const { data } = await apiClient.get<DocumentTypeVersion>(`/document-type-versions/${id}`);
  return data;
};

export const createDocumentTypeVersion = async (documentTypeId: string, payload: { schema_json: unknown }) => {
  const { data } = await apiClient.post<DocumentTypeVersion>(`/document-types/${documentTypeId}/versions`, payload);
  return data;
};

export const updateDocumentTypeVersion = async (id: string, payload: { schema_json: unknown }) => {
  const { data } = await apiClient.put<DocumentTypeVersion>(`/document-type-versions/${id}`, payload);
  return data;
};

export const publishDocumentTypeVersion = async (id: string) => {
  const { data } = await apiClient.post<DocumentTypeVersion>(`/document-type-versions/${id}/publish`);
  return data;
};

export const getPublishedDocumentTypeVersion = async (documentTypeId: string) => {
  const { data } = await apiClient.get<DocumentTypeVersion>(`/document-types/${documentTypeId}/published-version`);
  return data;
};

export const addSection = async (versionId: string, payload: SectionPayload) => {
  const { data } = await apiClient.post<DocumentTypeVersion>(`/document-type-versions/${versionId}/sections`, payload);
  return data;
};

export const updateSection = async (versionId: string, sectionCode: string, payload: SectionPayload) => {
  const { data } = await apiClient.put<DocumentTypeVersion>(
    `/document-type-versions/${versionId}/sections/${sectionCode}`,
    payload,
  );
  return data;
};

export const deleteSection = async (versionId: string, sectionCode: string) => {
  const { data } = await apiClient.delete<DocumentTypeVersion>(`/document-type-versions/${versionId}/sections/${sectionCode}`);
  return data;
};

export const addField = async (versionId: string, payload: FieldPayload) => {
  const { data } = await apiClient.post<DocumentTypeVersion>(`/document-type-versions/${versionId}/fields`, payload);
  return data;
};

export const updateField = async (versionId: string, fieldCode: string, payload: FieldPayload) => {
  const { data } = await apiClient.put<DocumentTypeVersion>(`/document-type-versions/${versionId}/fields/${fieldCode}`, payload);
  return data;
};

export const deleteField = async (versionId: string, fieldCode: string) => {
  const { data } = await apiClient.delete<DocumentTypeVersion>(`/document-type-versions/${versionId}/fields/${fieldCode}`);
  return data;
};

export const validateSchema = async (versionId: string) => {
  const { data } = await apiClient.post<SchemaValidationResult>(`/document-type-versions/${versionId}/validate-schema`);
  return data;
};
