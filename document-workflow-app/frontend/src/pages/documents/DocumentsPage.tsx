import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Space, Table, Tag, Typography } from "antd";
import { Link } from "react-router-dom";

import { getDocuments } from "../../entities/document";
import type { DocumentItem } from "../../entities/document";

export const DocumentsPage = () => {
  const { data = [], isLoading, isError, error } = useQuery({ queryKey: ["documents"], queryFn: getDocuments });
  const errorMessage = isError
    ? ((error as any)?.response?.data?.error?.message ?? (error as Error)?.message ?? "Ошибка загрузки документов")
    : null;

  return (
    <Card>
      {errorMessage ? <Alert type="error" showIcon style={{ marginBottom: 16 }} message={errorMessage} /> : null}
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Документы
        </Typography.Title>
        <Button type="primary">
          <Link to="/documents/new">Создать документ</Link>
        </Button>
      </Space>
      <Table
        loading={isLoading}
        rowKey="id"
        dataSource={data}
        columns={[
          { title: "Номер", dataIndex: "number" },
          { title: "Заголовок", dataIndex: "title" },
          { title: "Статус", dataIndex: "approval_status", render: (v: string) => <Tag>{v}</Tag> },
          {
            title: "Действие",
            render: (_, row: DocumentItem) => <Link to={`/documents/${row.id}`}>Открыть</Link>,
          },
        ]}
      />
    </Card>
  );
};
