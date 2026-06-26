import { apiClient } from "../../shared/api/axios";
import type { NotificationsResponse, UnreadCountResponse } from "./types";

export const getMyNotifications = async (params?: { limit?: number; offset?: number; is_read?: boolean }) => {
  const { data } = await apiClient.get<NotificationsResponse>("/notifications/my", { params });
  return data;
};

export const getUnreadNotificationCount = async () => {
  const { data } = await apiClient.get<UnreadCountResponse>("/notifications/unread-count");
  return data;
};

export const markNotificationRead = async (notificationId: string) => {
  const { data } = await apiClient.post<{ status: "read" }>(`/notifications/${notificationId}/read`);
  return data;
};

export const markAllNotificationsRead = async () => {
  const { data } = await apiClient.post<{ status: "read_all"; updated_count: number }>("/notifications/read-all");
  return data;
};
