import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Form, Input, Modal, Space, Table, Typography, message } from "antd";
import TextArea from "antd/es/input/TextArea";
import { useState } from "react";

import { apiClient, setUserIdHeader } from "../../shared/api/axios";

export const ApprovalRoutesPage = () => {
  const [createForm] = Form.useForm();
  const [versionForm] = Form.useForm();
  const [publishForm] = Form.useForm();

  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [versionModalOpen, setVersionModalOpen] = useState(false);
  const [publishModalOpen, setPublishModalOpen] = useState(false);

  const { data = [], refetch, isError, error } = useQuery({
    queryKey: ["routes"],
    queryFn: async () => {
      const { data } = await apiClient.get("/workflow/routes");
      return data;
    },
  });
  const loadErrorMessage = isError
    ? ((error as any)?.response?.data?.error?.message ?? (error as Error)?.message ?? "Ошибка загрузки маршрутов")
    : null;

  const createRouteMutation = useMutation({
    mutationFn: async (payload: any) => apiClient.post("/workflow/routes", payload),
    onSuccess: () => {
      message.success("Маршрут создан");
      createForm.resetFields();
      refetch();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка создания маршрута"),
  });

  const createVersionMutation = useMutation({
    mutationFn: async (payload: any) => apiClient.post(`/workflow/routes/${selectedRouteId}/versions`, payload),
    onSuccess: () => {
      message.success("Версия маршрута создана");
      setVersionModalOpen(false);
      versionForm.resetFields();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка создания версии маршрута"),
  });

  const publishVersionMutation = useMutation({
    mutationFn: async (payload: any) => {
      setUserIdHeader(payload.user_id);
      return apiClient.post(`/workflow/route-versions/${payload.version_id}/publish`);
    },
    onSuccess: () => {
      message.success("Версия опубликована");
      setPublishModalOpen(false);
      publishForm.resetFields();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка публикации версии"),
  });

  const onCreateRoute = (values: any) => {
    createRouteMutation.mutate({
      document_type_id: values.document_type_id,
      code: values.code,
      name: values.name,
      description: values.description,
      is_active: true,
    });
  };

  const onCreateVersion = (values: any) => {
    try {
      createVersionMutation.mutate({ route_schema_json: JSON.parse(values.route_schema_json) });
    } catch {
      message.error("Некорректный JSON route_schema_json");
    }
  };

  const onPublish = (values: any) => {
    publishVersionMutation.mutate(values);
  };

  return (
    <Card>
      {loadErrorMessage ? <Alert type="error" showIcon style={{ marginBottom: 16 }} message={loadErrorMessage} /> : null}
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Маршруты согласования
        </Typography.Title>
        <Space>
          <Button type="primary" onClick={() => setVersionModalOpen(true)} disabled={!selectedRouteId}>
            Создать версию маршрута
          </Button>
          <Button onClick={() => setPublishModalOpen(true)}>Publish версии</Button>
        </Space>
      </Space>

      <Form form={createForm} layout="vertical" onFinish={onCreateRoute}>
        <Space align="start" style={{ width: "100%" }}>
          <Form.Item name="document_type_id" label="Document Type ID" rules={[{ required: true }]}>
            <Input style={{ width: 260 }} placeholder="uuid" />
          </Form.Item>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}>
            <Input style={{ width: 220 }} />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input style={{ width: 240 }} />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input style={{ width: 260 }} />
          </Form.Item>
          <Form.Item label=" ">
            <Button type="primary" htmlType="submit" loading={createRouteMutation.isPending}>
              Создать маршрут
            </Button>
          </Form.Item>
        </Space>
      </Form>

      <Table
        rowKey="id"
        dataSource={data}
        rowSelection={{
          type: "radio",
          onChange: (selectedKeys) => setSelectedRouteId(String(selectedKeys[0] ?? "")),
        }}
        columns={[
          { title: "Код", dataIndex: "code" },
          { title: "Название", dataIndex: "name" },
          { title: "Document Type", dataIndex: "document_type_id" },
        ]}
      />

      <Modal title="Создать версию маршрута" open={versionModalOpen} onCancel={() => setVersionModalOpen(false)} footer={null}>
        <Form form={versionForm} layout="vertical" onFinish={onCreateVersion}>
          <Form.Item
            name="route_schema_json"
            label="route_schema_json"
            initialValue='{"steps": [{"order":1,"name":"Руководитель","type":"sequential","approverResolver":{"type":"specific_user","userId":"uuid"},"decisionPolicy":"all","slaHours":24}]}'
            rules={[{ required: true }]}
          >
            <TextArea rows={8} />
          </Form.Item>
          <Button htmlType="submit" type="primary" loading={createVersionMutation.isPending}>
            Создать
          </Button>
        </Form>
      </Modal>

      <Modal title="Publish версии маршрута" open={publishModalOpen} onCancel={() => setPublishModalOpen(false)} footer={null}>
        <Form form={publishForm} layout="vertical" onFinish={onPublish}>
          <Form.Item name="version_id" label="Route Version ID" rules={[{ required: true }]}>
            <Input placeholder="uuid" />
          </Form.Item>
          <Form.Item name="user_id" label="X-User-Id" rules={[{ required: true }]}>
            <Input placeholder="uuid" />
          </Form.Item>
          <Button htmlType="submit" type="primary" loading={publishVersionMutation.isPending}>
            Publish
          </Button>
        </Form>
      </Modal>
    </Card>
  );
};
