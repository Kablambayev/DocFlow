import { Button, Card, Space, Table, Tag, Typography } from "antd";

const data = [
  { id: "dt-1", code: "PAYMENT_REQUEST", name: "Заявка на оплату", is_active: true },
];

export const DocumentTypesPage = () => {
  return (
    <Card>
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Типы документов
        </Typography.Title>
        <Button type="primary">Создать тип</Button>
      </Space>
      <Table
        rowKey="id"
        dataSource={data}
        columns={[
          { title: "Код", dataIndex: "code" },
          { title: "Название", dataIndex: "name" },
          { title: "Активен", dataIndex: "is_active", render: (v: boolean) => <Tag color={v ? "green" : "red"}>{String(v)}</Tag> },
        ]}
      />
    </Card>
  );
};
