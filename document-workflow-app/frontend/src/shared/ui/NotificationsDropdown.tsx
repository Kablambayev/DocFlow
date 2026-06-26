import {
  BellOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  MessageOutlined,
  PaperClipOutlined,
  RollbackOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Empty, List, Popover, Space, Typography, message } from "antd";
import type { ReactNode } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  getMyNotifications,
  getUnreadNotificationCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../entities/notification";
import type { NotificationItem } from "../../entities/notification";
import { useAuth } from "../auth/useAuth";

const iconByType: Record<string, ReactNode> = {
  approval_task_created: <ClockCircleOutlined style={{ color: "#d48806" }} />,
  approval_task_approved: <CheckCircleOutlined style={{ color: "#389e0d" }} />,
  approval_task_rejected: <CloseCircleOutlined style={{ color: "#cf1322" }} />,
  document_approved: <CheckCircleOutlined style={{ color: "#389e0d" }} />,
  document_rejected: <CloseCircleOutlined style={{ color: "#cf1322" }} />,
  document_comment_created: <MessageOutlined style={{ color: "#1677ff" }} />,
  document_file_uploaded: <PaperClipOutlined style={{ color: "#0a6e6e" }} />,
  document_withdrawn: <RollbackOutlined style={{ color: "#595959" }} />,
};

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const formatDateTime = (value: string) => new Date(value).toLocaleString();

export const NotificationsDropdown = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { currentUserId, hasPermission } = useAuth();
  const [open, setOpen] = useState(false);
  const canRead = Boolean(currentUserId) && hasPermission("notification.read");
  const canUpdate = hasPermission("notification.update");

  const unreadQuery = useQuery({
    queryKey: ["notifications", "unread-count", currentUserId],
    queryFn: getUnreadNotificationCount,
    enabled: canRead,
    refetchInterval: 30000,
    retry: false,
  });

  const notificationsQuery = useQuery({
    queryKey: ["notifications", "my", currentUserId],
    queryFn: () => getMyNotifications({ limit: 10 }),
    enabled: canRead && open,
    retry: false,
  });

  const invalidateNotifications = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count", currentUserId] }),
      queryClient.invalidateQueries({ queryKey: ["notifications", "my", currentUserId] }),
    ]);
  };

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: invalidateNotifications,
    onError: (error) => message.error(apiError(error, "Ошибка обновления уведомления")),
  });

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: async () => {
      await invalidateNotifications();
      message.success("Уведомления прочитаны");
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления уведомлений")),
  });

  const openNotification = async (item: NotificationItem) => {
    if (canUpdate && !item.is_read) {
      await markReadMutation.mutateAsync(item.id);
    }
    setOpen(false);
    if (item.document_id) {
      navigate(`/documents/${item.document_id}${item.task_id ? `?taskId=${item.task_id}` : ""}`);
      return;
    }
    if (item.task_id) {
      navigate("/tasks");
    }
  };

  if (!canRead) return null;

  const items = notificationsQuery.data?.items ?? [];
  const content = (
    <Space direction="vertical" size={8} style={{ width: 360, maxWidth: "80vw" }}>
      <Space style={{ width: "100%", justifyContent: "space-between" }}>
        <Typography.Text strong>Уведомления</Typography.Text>
        <Button
          size="small"
          disabled={!canUpdate || (unreadQuery.data?.unread_count ?? 0) === 0}
          loading={markAllMutation.isPending}
          onClick={() => markAllMutation.mutate()}
        >
          Прочитать все
        </Button>
      </Space>
      {notificationsQuery.isError ? (
        <Typography.Text type="danger">{apiError(notificationsQuery.error, "Ошибка загрузки уведомлений")}</Typography.Text>
      ) : null}
      {items.length === 0 && !notificationsQuery.isLoading ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Нет уведомлений" /> : null}
      <List
        loading={notificationsQuery.isLoading}
        dataSource={items}
        renderItem={(item) => (
          <List.Item
            onClick={() => void openNotification(item)}
            style={{
              cursor: "pointer",
              padding: "10px 8px",
              background: item.is_read ? "#ffffff" : "#f0f7ff",
              borderRadius: 6,
              marginBottom: 4,
            }}
          >
            <List.Item.Meta
              avatar={
                <Badge dot={!item.is_read} offset={[2, 2]}>
                  {iconByType[item.type] ?? <BellOutlined />}
                </Badge>
              }
              title={<Typography.Text strong={!item.is_read}>{item.title}</Typography.Text>}
              description={
                <Space direction="vertical" size={2}>
                  {item.message ? <Typography.Text type="secondary">{item.message}</Typography.Text> : null}
                  <Typography.Text type="secondary">{formatDateTime(item.created_at)}</Typography.Text>
                </Space>
              }
            />
          </List.Item>
        )}
      />
      <Button block disabled>
        Показать все
      </Button>
    </Space>
  );

  return (
    <Popover trigger="click" open={open} onOpenChange={setOpen} content={content} placement="bottomRight">
      <Badge count={unreadQuery.data?.unread_count ?? 0} size="small">
        <Button icon={<BellOutlined />} />
      </Badge>
    </Popover>
  );
};
