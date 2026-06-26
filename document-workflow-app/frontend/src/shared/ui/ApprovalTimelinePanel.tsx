import { useQuery } from "@tanstack/react-query";
import { Alert, Empty, List, Space, Tag, Timeline, Typography } from "antd";
import dayjs from "dayjs";

import { getApprovalTimeline } from "../../entities/timeline";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const statusColor: Record<string, string> = {
  Pending: "gold",
  Approved: "green",
  Rejected: "red",
  Cancelled: "default",
  Completed: "green",
  OnApproval: "blue",
};

interface ApprovalTimelinePanelProps {
  documentId: string;
}

export const ApprovalTimelinePanel = ({ documentId }: ApprovalTimelinePanelProps) => {
  const timelineQuery = useQuery({
    queryKey: ["approval-timeline", documentId],
    queryFn: () => getApprovalTimeline(documentId),
    enabled: Boolean(documentId),
  });

  if (timelineQuery.isError) {
    return <Alert type="error" showIcon message={apiError(timelineQuery.error, "Ошибка загрузки ленты согласования")} />;
  }

  if (!timelineQuery.isLoading && !timelineQuery.data?.process) {
    return <Empty description="Согласование еще не запускалось" />;
  }

  const items =
    timelineQuery.data?.steps.map((step) => ({
      color: statusColor[step.status] === "red" ? "red" : statusColor[step.status] === "green" ? "green" : "blue",
      children: (
        <Space direction="vertical" size={8} style={{ width: "100%" }}>
          <Space wrap>
            <Typography.Text strong>
              {step.step_order}. {step.step_name}
            </Typography.Text>
            <Tag color={statusColor[step.status]}>{step.status}</Tag>
          </Space>
          <List
            size="small"
            dataSource={step.tasks}
            renderItem={(task) => (
              <List.Item>
                <Space direction="vertical" size={2}>
                  <Space wrap>
                    <Typography.Text>{task.approver_name ?? task.approver_id}</Typography.Text>
                    <Tag color={statusColor[task.status]}>{task.status}</Tag>
                    <Typography.Text type="secondary">
                      {task.completed_at ? dayjs(task.completed_at).format("DD.MM.YYYY HH:mm") : dayjs(task.created_at).format("DD.MM.YYYY HH:mm")}
                    </Typography.Text>
                  </Space>
                  {task.comment ? <Typography.Text type="secondary">{task.comment}</Typography.Text> : null}
                </Space>
              </List.Item>
            )}
          />
        </Space>
      ),
    })) ?? [];

  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      {timelineQuery.data?.process ? (
        <Space wrap>
          <Typography.Text strong>Процесс</Typography.Text>
          <Tag color={statusColor[timelineQuery.data.process.status]}>{timelineQuery.data.process.status}</Tag>
          <Typography.Text type="secondary">{dayjs(timelineQuery.data.process.started_at).format("DD.MM.YYYY HH:mm")}</Typography.Text>
        </Space>
      ) : null}
      <Timeline pending={timelineQuery.isLoading ? "Загрузка..." : false} items={items} />
    </Space>
  );
};
