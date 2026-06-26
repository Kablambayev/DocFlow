import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Form, Input, InputNumber, Space, Table, Typography, message } from "antd";
import TextArea from "antd/es/input/TextArea";

import { apiClient, setUserIdHeader } from "../../shared/api/axios";

export const ApprovalMatrixPage = () => {
  const [form] = Form.useForm();

  const { data = [], refetch, isError, error } = useQuery({
    queryKey: ["matrix-rules"],
    queryFn: async () => {
      const { data } = await apiClient.get("/workflow/matrix-rules");
      return data;
    },
  });
  const loadErrorMessage = isError
    ? ((error as any)?.response?.data?.error?.message ?? (error as Error)?.message ?? "Ошибка загрузки правил")
    : null;

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      setUserIdHeader(payload.user_id);
      return apiClient.post("/workflow/matrix-rules", payload.body);
    },
    onSuccess: () => {
      message.success("Правило создано");
      form.resetFields();
      refetch();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка создания правила"),
  });

  const deleteMutation = useMutation({
    mutationFn: async (payload: { id: string; user_id: string }) => {
      setUserIdHeader(payload.user_id);
      return apiClient.delete(`/workflow/matrix-rules/${payload.id}`);
    },
    onSuccess: () => {
      message.success("Правило удалено (soft delete)");
      refetch();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка удаления правила"),
  });

  const onCreate = (values: any) => {
    try {
      createMutation.mutate({
        user_id: values.user_id,
        body: {
          document_type_id: values.document_type_id,
          priority: values.priority,
          name: values.name,
          condition_json: JSON.parse(values.condition_json),
          route_id: values.route_id,
          is_active: true,
        },
      });
    } catch {
      message.error("Некорректный JSON condition_json");
    }
  };

  return (
    <Card>
      {loadErrorMessage ? <Alert type="error" showIcon style={{ marginBottom: 16 }} message={loadErrorMessage} /> : null}
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Матрица согласования
        </Typography.Title>
      </Space>

      <Form form={form} layout="vertical" onFinish={onCreate}>
        <Space align="start" style={{ width: "100%" }}>
          <Form.Item name="user_id" label="X-User-Id" rules={[{ required: true }]}>
            <Input style={{ width: 220 }} placeholder="uuid" />
          </Form.Item>
          <Form.Item name="document_type_id" label="Document Type ID" rules={[{ required: true }]}>
            <Input style={{ width: 260 }} placeholder="uuid" />
          </Form.Item>
          <Form.Item name="route_id" label="Route ID" rules={[{ required: true }]}>
            <Input style={{ width: 260 }} placeholder="uuid" />
          </Form.Item>
          <Form.Item name="priority" label="Priority" rules={[{ required: true }]}>
            <InputNumber style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input style={{ width: 220 }} />
          </Form.Item>
          <Form.Item label=" ">
            <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
              Добавить правило
            </Button>
          </Form.Item>
        </Space>
        <Form.Item
          name="condition_json"
          label="condition_json"
          initialValue='{"operator":"and","conditions":[{"field":"amount","operator":">=","value":1000000}]}'
          rules={[{ required: true }]}
        >
          <TextArea rows={5} />
        </Form.Item>
      </Form>

      <Table
        rowKey="id"
        dataSource={data}
        columns={[
          { title: "Правило", dataIndex: "name" },
          { title: "Приоритет", dataIndex: "priority" },
          { title: "Активно", dataIndex: "is_active", render: (v: boolean) => String(v) },
          {
            title: "Действие",
            render: (_, row: any) => (
              <Button danger onClick={() => deleteMutation.mutate({ id: row.id, user_id: form.getFieldValue("user_id") })}>
                Soft delete
              </Button>
            ),
          },
        ]}
      />
    </Card>
  );
};
