import { useMutation, useQuery } from "@tanstack/react-query";
import { Button, Card, Descriptions, Form, Input, Space, Tag, Typography, message } from "antd";
import TextArea from "antd/es/input/TextArea";
import { useEffect } from "react";
import { useParams } from "react-router-dom";

import { apiClient, setUserIdHeader } from "../../shared/api/axios";

const editableStatuses = ["Draft", "Withdrawn"];

export const DocumentCardPage = () => {
  const { id } = useParams();
  const [form] = Form.useForm();

  const { data: document, refetch } = useQuery({
    queryKey: ["document", id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/documents/${id}`);
      return data;
    },
    enabled: Boolean(id),
  });

  useEffect(() => {
    if (document) {
      form.setFieldsValue({ title: document.title, data_json: JSON.stringify(document.data_json ?? {}, null, 2) });
    }
  }, [document, form]);

  const updateMutation = useMutation({
    mutationFn: async (payload: any) => apiClient.put(`/documents/${id}`, payload),
    onSuccess: () => {
      message.success("Документ обновлен");
      refetch();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка обновления"),
  });

  const submitMutation = useMutation({
    mutationFn: async () => apiClient.post(`/documents/${id}/submit`),
    onSuccess: () => {
      message.success("Документ отправлен на согласование");
      refetch();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка отправки"),
  });

  const withdrawMutation = useMutation({
    mutationFn: async () => apiClient.post(`/documents/${id}/withdraw`),
    onSuccess: () => {
      message.success("Документ отозван");
      refetch();
    },
    onError: (error: any) => message.error(error?.response?.data?.error?.message ?? "Ошибка отзыва"),
  });

  const onSave = (values: any) => {
    try {
      setUserIdHeader(values.current_user_id ?? null);
      updateMutation.mutate({ title: values.title, data_json: JSON.parse(values.data_json || "{}") });
    } catch {
      message.error("Некорректный JSON в data_json");
    }
  };

  if (!document) {
    return <Card loading />;
  }

  const canEdit = editableStatuses.includes(document.approval_status);
  const canSubmit = editableStatuses.includes(document.approval_status);
  const canWithdraw = document.approval_status === "OnApproval";

  return (
    <Card title={`Карточка документа ${id}`}>
      <Descriptions bordered column={1}>
        <Descriptions.Item label="Номер">{document.number}</Descriptions.Item>
        <Descriptions.Item label="Статус">
          <Tag>{document.approval_status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Автор">{document.author_id}</Descriptions.Item>
      </Descriptions>

      <Typography.Title level={5} style={{ marginTop: 16 }}>
        Данные документа
      </Typography.Title>

      <Form form={form} layout="vertical" onFinish={onSave}>
        <Form.Item name="current_user_id" label="Current User ID (X-User-Id)">
          <Input placeholder="uuid" />
        </Form.Item>
        <Form.Item name="title" label="Заголовок">
          <Input disabled={!canEdit} />
        </Form.Item>
        <Form.Item name="data_json" label="data_json">
          <TextArea rows={10} disabled={!canEdit} />
        </Form.Item>

        <Space>
          {canEdit ? (
            <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>
              Сохранить
            </Button>
          ) : null}
          {canSubmit ? (
            <Button type="primary" loading={submitMutation.isPending} onClick={() => submitMutation.mutate()}>
              Отправить на согласование
            </Button>
          ) : null}
          {canWithdraw ? (
            <Button danger loading={withdrawMutation.isPending} onClick={() => withdrawMutation.mutate()}>
              Отозвать
            </Button>
          ) : null}
        </Space>
      </Form>
    </Card>
  );
};
