import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Input, Space, Table, Tag, Typography, message } from "antd";
import { useState } from "react";

import { apiClient, setUserIdHeader } from "../../shared/api/axios";

export const MyTasksPage = () => {
  const [userId, setUserId] = useState(localStorage.getItem("docflow_user_id") ?? "");
  const [commentByTaskId, setCommentByTaskId] = useState<Record<string, string>>({});

  const { data = [], refetch, isError, error } = useQuery({
    queryKey: ["my-tasks", userId],
    queryFn: async () => {
      if (!userId) return [];
      setUserIdHeader(userId);
      const { data } = await apiClient.get("/workflow/tasks/my");
      return data;
    },
  });
  const loadErrorMessage = isError
    ? ((error as any)?.response?.data?.error?.message ?? (error as Error)?.message ?? "Ошибка загрузки задач")
    : null;

  const approveMutation = useMutation({
    mutationFn: async (taskId: string) => {
      setUserIdHeader(userId);
      return apiClient.post(`/workflow/tasks/${taskId}/approve`, { comment: commentByTaskId[taskId] || null });
    },
    onSuccess: () => {
      message.success("Задача согласована");
      refetch();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка согласования"),
  });

  const rejectMutation = useMutation({
    mutationFn: async (taskId: string) => {
      setUserIdHeader(userId);
      return apiClient.post(`/workflow/tasks/${taskId}/reject`, { comment: commentByTaskId[taskId] || null });
    },
    onSuccess: () => {
      message.success("Задача отклонена");
      refetch();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка отклонения"),
  });

  return (
    <Card>
      <Typography.Title level={4}>Мои задачи согласования</Typography.Title>
      {loadErrorMessage ? <Alert type="error" showIcon style={{ marginBottom: 12 }} message={loadErrorMessage} /> : null}
      <Space style={{ marginBottom: 12 }}>
        <Input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="X-User-Id"
          style={{ width: 380 }}
        />
        <Button onClick={() => refetch()}>Загрузить задачи</Button>
      </Space>
      <Table
        rowKey="id"
        dataSource={data}
        columns={[
          { title: "Шаг", dataIndex: "step_name" },
          { title: "Статус", dataIndex: "status", render: (v: string) => <Tag color="gold">{v}</Tag> },
          {
            title: "Комментарий",
            render: (_, row: any) => (
              <Input
                value={commentByTaskId[row.id] || ""}
                onChange={(e) => setCommentByTaskId((prev) => ({ ...prev, [row.id]: e.target.value }))}
                placeholder="Комментарий"
              />
            ),
          },
          {
            title: "Действия",
            render: (_, row: any) => (
              <Space>
                <Button type="primary" onClick={() => approveMutation.mutate(row.id)}>
                  Approve
                </Button>
                <Button danger onClick={() => rejectMutation.mutate(row.id)}>
                  Reject
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
};
