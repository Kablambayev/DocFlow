import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Input, Space, Table, Tag, Typography, message } from "antd";
import { useState } from "react";

import { approveTask, getMyTasks, rejectTask } from "../../entities/workflow";
import type { WorkflowTask } from "../../entities/workflow";
import { setUserIdHeader } from "../../shared/api/axios";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

export const MyTasksV2Page = () => {
  const [userId, setUserId] = useState(localStorage.getItem("docflow_user_id") ?? "");
  const [commentByTaskId, setCommentByTaskId] = useState<Record<string, string>>({});

  const tasksQuery = useQuery({
    queryKey: ["my-tasks", userId],
    queryFn: () => {
      if (!userId) return Promise.resolve([]);
      setUserIdHeader(userId);
      return getMyTasks();
    },
  });

  const approveMutation = useMutation({
    mutationFn: (taskId: string) => {
      setUserIdHeader(userId);
      return approveTask(taskId, { comment: commentByTaskId[taskId] || null });
    },
    onSuccess: () => {
      message.success("Задача согласована");
      void tasksQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка согласования")),
  });

  const rejectMutation = useMutation({
    mutationFn: (taskId: string) => {
      setUserIdHeader(userId);
      return rejectTask(taskId, { comment: commentByTaskId[taskId] || null });
    },
    onSuccess: () => {
      message.success("Задача отклонена");
      void tasksQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка отклонения")),
  });

  return (
    <Card>
      <Typography.Title level={4}>Мои задачи согласования</Typography.Title>
      {tasksQuery.isError ? <Alert type="error" showIcon style={{ marginBottom: 12 }} message={apiError(tasksQuery.error, "Ошибка загрузки задач")} /> : null}
      <Space style={{ marginBottom: 12 }}>
        <Input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="X-User-Id" style={{ width: 380 }} />
        <Button onClick={() => void tasksQuery.refetch()}>Загрузить задачи</Button>
      </Space>
      <Table<WorkflowTask>
        rowKey="id"
        loading={tasksQuery.isLoading}
        dataSource={tasksQuery.data ?? []}
        columns={[
          { title: "Шаг", dataIndex: "step_name" },
          { title: "Статус", dataIndex: "status", render: (value: string) => <Tag color="gold">{value}</Tag> },
          {
            title: "Комментарий",
            render: (_, row) => (
              <Input
                value={commentByTaskId[row.id] || ""}
                onChange={(event) => setCommentByTaskId((prev) => ({ ...prev, [row.id]: event.target.value }))}
                placeholder="Комментарий"
              />
            ),
          },
          {
            title: "Действия",
            render: (_, row) => (
              <Space>
                <Button type="primary" onClick={() => approveMutation.mutate(row.id)}>Approve</Button>
                <Button danger onClick={() => rejectMutation.mutate(row.id)}>Reject</Button>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
};
