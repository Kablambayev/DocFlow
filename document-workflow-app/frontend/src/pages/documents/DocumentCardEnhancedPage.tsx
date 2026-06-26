import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Collapse, Descriptions, Form, Input, Space, Tag, Typography, message } from "antd";
import { useEffect } from "react";
import { useParams } from "react-router-dom";

import { getDocument, submitDocument, updateDocument, withdrawDocument } from "../../entities/document";
import { getDocumentTypeVersion } from "../../entities/document-type";
import { setUserIdHeader } from "../../shared/api/axios";
import { DynamicFormRenderer, normalizeDynamicInitialValues } from "../../shared/ui/DynamicFormRenderer";

const editableStatuses = ["Draft", "Withdrawn"];
const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

export const DocumentCardEnhancedPage = () => {
  const { id } = useParams();
  const [form] = Form.useForm();

  const documentQuery = useQuery({ queryKey: ["document", id], queryFn: () => getDocument(id ?? ""), enabled: Boolean(id) });
  const versionQuery = useQuery({
    queryKey: ["document-type-version", documentQuery.data?.document_type_version_id],
    queryFn: () => getDocumentTypeVersion(documentQuery.data?.document_type_version_id ?? ""),
    enabled: Boolean(documentQuery.data?.document_type_version_id),
  });

  const document = documentQuery.data;
  const schema = versionQuery.data?.schema_json;
  const canEdit = document ? editableStatuses.includes(document.approval_status) : false;
  const canSubmit = canEdit;
  const canWithdraw = document?.approval_status === "OnApproval";

  useEffect(() => {
    if (document && schema) {
      form.setFieldsValue({
        current_user_id: localStorage.getItem("docflow_user_id") ?? "",
        title: document.title,
        ...normalizeDynamicInitialValues(document.data_json, schema),
      });
    }
  }, [document, form, schema]);

  const updateMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const data_json: Record<string, unknown> = {};
      for (const section of schema?.sections ?? []) {
        for (const field of section.fields) {
          data_json[field.code] = values[field.code];
        }
      }
      return updateDocument(id ?? "", { title: String(values.title ?? document?.title ?? ""), data_json });
    },
    onSuccess: () => {
      message.success("Документ обновлен");
      void documentQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления")),
  });

  const submitMutation = useMutation({
    mutationFn: () => submitDocument(id ?? ""),
    onSuccess: () => {
      message.success("Документ отправлен на согласование");
      void documentQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка отправки")),
  });

  const withdrawMutation = useMutation({
    mutationFn: () => withdrawDocument(id ?? ""),
    onSuccess: () => {
      message.success("Документ отозван");
      void documentQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка отзыва")),
  });

  const onFinish = (values: Record<string, unknown>) => {
    setUserIdHeader(values.current_user_id ? String(values.current_user_id) : null);
    updateMutation.mutate(values);
  };

  if (documentQuery.isLoading || !document) return <Card loading />;

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {documentQuery.isError ? <Alert type="error" showIcon message={apiError(documentQuery.error, "Ошибка загрузки документа")} /> : null}
      <Card title={`Документ ${document.number}`}>
        <Descriptions bordered column={1}>
          <Descriptions.Item label="Номер">{document.number}</Descriptions.Item>
          <Descriptions.Item label="Заголовок">{document.title}</Descriptions.Item>
          <Descriptions.Item label="Статус"><Tag>{document.approval_status}</Tag></Descriptions.Item>
          <Descriptions.Item label="Автор">{document.author_id}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Данные документа">
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="current_user_id" label="Current User ID (X-User-Id)">
            <Input placeholder="uuid" />
          </Form.Item>
          <Form.Item name="title" label="Заголовок" rules={[{ required: true }]}>
            <Input disabled={!canEdit} />
          </Form.Item>
          {schema ? <DynamicFormRenderer schema={schema} disabled={!canEdit} /> : <Alert type="info" showIcon message="Схема формы не загружена." />}
          <Space>
            {canEdit ? <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>Сохранить</Button> : null}
            {canSubmit ? <Button type="primary" loading={submitMutation.isPending} onClick={() => submitMutation.mutate()}>Отправить на согласование</Button> : null}
            {canWithdraw ? <Button danger loading={withdrawMutation.isPending} onClick={() => withdrawMutation.mutate()}>Отозвать</Button> : null}
            <Button onClick={() => void documentQuery.refetch()}>Обновить</Button>
          </Space>
        </Form>
        <Collapse
          style={{ marginTop: 16 }}
          items={[{ key: "debug", label: "Raw data_json", children: <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(document.data_json, null, 2)}</pre> }]}
        />
      </Card>

      <Card>
        <Typography.Title level={5}>История согласования</Typography.Title>
        <Typography.Text type="secondary">TODO: подключить ленту audit/workflow history.</Typography.Text>
      </Card>
    </Space>
  );
};
