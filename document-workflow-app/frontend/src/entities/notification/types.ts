export interface NotificationItem {
  id: string;
  recipient_id: string;
  actor_id?: string | null;
  actor_name?: string | null;
  type: string;
  title: string;
  message?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  document_id?: string | null;
  task_id?: string | null;
  payload: Record<string, unknown>;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationsResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}
