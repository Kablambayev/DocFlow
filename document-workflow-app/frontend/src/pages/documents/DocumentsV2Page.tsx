import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Space, Table, Tag, Typography } from "antd";
import { Link } from "react-router-dom";

import { getDocuments } from "../../entities/document";
import type { DocumentItem } from "../../entities/document";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

export const DocumentsV2Page = () => {
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: getDocuments });

  return (
    <Card>
      {documentsQuery.isError ? <Alert type="error" showIcon style={{ marginBottom: 16 }} message={apiError(documentsQuery.error, "Ошибка загрузки документов")} /> : null}
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>Документы</Typography.Title>
        <Button type="primary"><Link to="/documents/new">Создать документ</Link></Button>
      </Space>
      <Table<DocumentItem>
        loading={documentsQuery.isLoading}
        rowKey="id"
        dataSource={documentsQuery.data ?? []}
        columns={[
          { title: "Номер", dataIndex: "number" },
          { title: "Заголовок", dataIndex: "title" },
          { title: "Статус", dataIndex: "approval_status", render: (value: string) => <Tag>{value}</Tag> },
          { title: "Дата", dataIndex: "document_date", render: (value: string) => new Date(value).toLocaleString() },
          { title: "Действие", render: (_, row) => <Link to={`/documents/${row.id}`}>Открыть</Link> },
        ]}
      />
    </Card>
  );
};
