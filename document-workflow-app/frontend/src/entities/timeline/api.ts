import { apiClient } from "../../shared/api/axios";
import type { ApprovalTimeline, TimelineItem } from "./types";

export const getDocumentTimeline = async (documentId: string) => {
  const { data } = await apiClient.get<TimelineItem[]>(`/documents/${documentId}/timeline`);
  return data;
};

export const getApprovalTimeline = async (documentId: string) => {
  const { data } = await apiClient.get<ApprovalTimeline>(`/documents/${documentId}/approval-timeline`);
  return data;
};
