import { apiClient } from "../../shared/api/axios";
import type { CreateCommentPayload, DocumentComment, UpdateCommentPayload } from "./types";

export const getDocumentComments = async (documentId: string) => {
  const { data } = await apiClient.get<DocumentComment[]>(`/documents/${documentId}/comments`);
  return data;
};

export const createDocumentComment = async (documentId: string, payload: CreateCommentPayload) => {
  const { data } = await apiClient.post<DocumentComment>(`/documents/${documentId}/comments`, payload);
  return data;
};

export const updateDocumentComment = async (commentId: string, payload: UpdateCommentPayload) => {
  const { data } = await apiClient.put<DocumentComment>(`/comments/${commentId}`, payload);
  return data;
};

export const deleteDocumentComment = async (commentId: string) => {
  const { data } = await apiClient.delete<{ status: string }>(`/comments/${commentId}`);
  return data;
};
