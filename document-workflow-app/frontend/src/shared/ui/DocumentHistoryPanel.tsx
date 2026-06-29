import { useQuery } from "@tanstack/react-query";
import { Alert, Empty, Space, Tag, Timeline, Typography } from "antd";
import dayjs from "dayjs";

import { getDocumentTimeline } from "../../entities/timeline";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const typeColor: Record<string, string> = {
  comment_added: "blue",
  file_uploaded: "green",
  file_deleted: "red",
  document_comment_created: "blue",
  document_comment_updated: "gold",
  document_comment_deleted: "red",
  integration_1c_payment_request_send_started: "gold",
  integration_1c_payment_request_created: "green",
  integration_1c_payment_request_already_exists: "blue",
  integration_1c_payment_request_failed: "red",
};

interface DocumentHistoryPanelProps {
  documentId: string;
}

export const DocumentHistoryPanel = ({ documentId }: DocumentHistoryPanelProps) => {
  const timelineQuery = useQuery({
    queryKey: ["document-timeline", documentId],
    queryFn: () => getDocumentTimeline(documentId),
    enabled: Boolean(documentId),
  });

  if (timelineQuery.isError) {
    return <Alert type="error" showIcon message={apiError(timelineQuery.error, "Ошибка загрузки истории документа")} />;
  }

  if (!timelineQuery.isLoading && timelineQuery.data?.length === 0) {
    return <Empty description="История пока пустая" />;
  }

  const items =
    timelineQuery.data?.map((item) => ({
      color: typeColor[item.type] === "red" ? "red" : typeColor[item.type] === "green" ? "green" : "blue",
      children: (
        <Space direction="vertical" size={2}>
          <Space wrap>
            <Typography.Text strong>{item.title}</Typography.Text>
            <Tag color={typeColor[item.type]}>{item.type}</Tag>
            <Typography.Text type="secondary">{dayjs(item.created_at).format("DD.MM.YYYY HH:mm")}</Typography.Text>
          </Space>
          <Typography.Text type="secondary">{item.user_name ?? item.user_id ?? "System"}</Typography.Text>
          {item.description ? <Typography.Paragraph style={{ marginBottom: 0, whiteSpace: "pre-wrap" }}>{item.description}</Typography.Paragraph> : null}
        </Space>
      ),
    })) ?? [];

  return <Timeline pending={timelineQuery.isLoading ? "Загрузка..." : false} items={items} />;
};
