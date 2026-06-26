import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Collapse, DatePicker, Form, Input, Select, Space, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { createDocument } from "../../entities/document";
import { getActiveDocumentTypes, getPublishedDocumentTypeVersion } from "../../entities/document-type";
import { setUserIdHeader } from "../../shared/api/axios";
import { DynamicFormRenderer } from "../../shared/ui/DynamicFormRenderer";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

export const CreateDocumentV2Page = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const selectedDocumentTypeId = Form.useWatch("document_type_id", form);
  const typesQuery = useQuery({ queryKey: ["active-document-types"], queryFn: getActiveDocumentTypes });
  const versionQuery = useQuery({
    queryKey: ["published-document-type-version", selectedDocumentTypeId],
    queryFn: () => getPublishedDocumentTypeVersion(selectedDocumentTypeId),
    enabled: Boolean(selectedDocumentTypeId),
  });
  const schema = versionQuery.data?.schema_json;
  const dynamicFieldCodes = useMemo(() => new Set(schema?.sections.flatMap((section) => section.fields.map((field) => field.code)) ?? []), [schema]);

  useEffect(() => {
    if (versionQuery.data) form.setFieldValue("document_type_version_id", versionQuery.data.id);
  }, [form, versionQuery.data]);

  const createMutation = useMutation({
    mutationFn: createDocument,
    onSuccess: (document) => {
      message.success("Документ создан");
      navigate(`/documents/${document.id}`);
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания документа")),
  });

  const onFinish = (values: Record<string, unknown>) => {
    const currentUserId = String(values.current_user_id ?? values.author_id ?? "");
    setUserIdHeader(currentUserId || null);
    const data_json: Record<string, unknown> = {};
    for (const code of dynamicFieldCodes) data_json[code] = values[code];
    createMutation.mutate({
      document_type_id: String(values.document_type_id),
      document_type_version_id: String(values.document_type_version_id),
      number: String(values.number),
      document_date: dayjs(values.document_date as string).toISOString(),
      author_id: String(values.author_id),
      organization_id: values.organization_id ? String(values.organization_id) : null,
      department_id: values.department_id ? String(values.department_id) : null,
      title: String(values.title),
      data_json,
    });
  };

  return (
    <Card title="Создание документа">
      {typesQuery.isError ? <Alert type="error" showIcon message={apiError(typesQuery.error, "Ошибка загрузки типов документов")} style={{ marginBottom: 16 }} /> : null}
      {versionQuery.isError ? <Alert type="error" showIcon message={apiError(versionQuery.error, "Ошибка загрузки опубликованной версии")} style={{ marginBottom: 16 }} /> : null}
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Space align="start" wrap style={{ width: "100%" }}>
          <Form.Item name="current_user_id" label="Current User ID (X-User-Id)"><Input style={{ width: 260 }} placeholder="uuid" /></Form.Item>
          <Form.Item name="author_id" label="Author ID" rules={[{ required: true }]}><Input style={{ width: 260 }} placeholder="uuid" /></Form.Item>
          <Form.Item name="document_type_id" label="Тип документа" rules={[{ required: true }]}>
            <Select loading={typesQuery.isLoading} style={{ width: 320 }} options={(typesQuery.data ?? []).map((item) => ({ value: item.id, label: `${item.code} - ${item.name}` }))} />
          </Form.Item>
          <Form.Item name="document_type_version_id" label="Версия формы" rules={[{ required: true }]}><Input style={{ width: 260 }} disabled /></Form.Item>
          <Form.Item name="number" label="Номер" rules={[{ required: true }]}><Input style={{ width: 180 }} placeholder="PAY-000001" /></Form.Item>
          <Form.Item name="document_date" label="Дата документа" rules={[{ required: true }]} initialValue={dayjs()}><DatePicker showTime style={{ width: 220 }} /></Form.Item>
          <Form.Item name="title" label="Заголовок" rules={[{ required: true }]}><Input style={{ width: 360 }} /></Form.Item>
          <Form.Item name="organization_id" label="Organization ID"><Input style={{ width: 260 }} /></Form.Item>
          <Form.Item name="department_id" label="Department ID"><Input style={{ width: 260 }} /></Form.Item>
        </Space>
        {schema ? <DynamicFormRenderer schema={schema} /> : <Alert type="info" showIcon message="Выберите тип документа с опубликованной версией формы." />}
        <Collapse style={{ marginTop: 16 }} items={[{ key: "debug", label: "Debug schema", children: <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(schema ?? {}, null, 2)}</pre> }]} />
        <Button type="primary" htmlType="submit" loading={createMutation.isPending} style={{ marginTop: 16 }}>Создать документ</Button>
      </Form>
    </Card>
  );
};
