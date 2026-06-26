import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Checkbox, Divider, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography, message } from "antd";
import { useMemo, useState } from "react";

import {
  addField,
  addSection,
  createDocumentType,
  createDocumentTypeVersion,
  deleteField,
  deleteSection,
  getDocumentTypes,
  getDocumentTypeVersions,
  publishDocumentTypeVersion,
  validateSchema,
} from "../../entities/document-type";
import type { DocumentFieldSchema, DocumentSectionSchema, DocumentType, FieldPayload, FieldType } from "../../entities/document-type";
import { DynamicFormRenderer } from "../../shared/ui/DynamicFormRenderer";

const defaultSchema = { sections: [{ code: "main", name: "Основные данные", sortOrder: 10, fields: [] }] };
const fieldTypes: FieldType[] = ["string", "text", "integer", "decimal", "money", "date", "datetime", "boolean", "enum", "reference", "file", "table"];

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

export const DocumentTypesAdminPage = () => {
  const [typeForm] = Form.useForm();
  const [sectionForm] = Form.useForm();
  const [fieldForm] = Form.useForm();
  const [createOpen, setCreateOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const typesQuery = useQuery({ queryKey: ["document-types"], queryFn: getDocumentTypes });
  const versionsQuery = useQuery({
    queryKey: ["document-type-versions", selectedTypeId],
    queryFn: () => getDocumentTypeVersions(selectedTypeId ?? ""),
    enabled: Boolean(selectedTypeId),
  });

  const selectedVersion = useMemo(
    () => versionsQuery.data?.find((item) => item.id === selectedVersionId) ?? versionsQuery.data?.[0],
    [selectedVersionId, versionsQuery.data],
  );
  const isDraft = selectedVersion?.status === "draft" || selectedVersion?.status === "Draft";
  const refreshVersions = () => void versionsQuery.refetch();

  const createTypeMutation = useMutation({
    mutationFn: createDocumentType,
    onSuccess: (created) => {
      message.success("Тип документа создан");
      setCreateOpen(false);
      typeForm.resetFields();
      setSelectedTypeId(created.id);
      void typesQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания типа документа")),
  });

  const createVersionMutation = useMutation({
    mutationFn: () => createDocumentTypeVersion(selectedTypeId ?? "", { schema_json: defaultSchema }),
    onSuccess: (version) => {
      message.success("Черновик версии создан");
      setSelectedVersionId(version.id);
      refreshVersions();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания версии")),
  });

  const addSectionMutation = useMutation({
    mutationFn: (payload: { code: string; name: string; sortOrder: number }) => addSection(selectedVersion?.id ?? "", payload),
    onSuccess: () => {
      message.success("Секция добавлена");
      sectionForm.resetFields();
      refreshVersions();
    },
    onError: (error) => message.error(apiError(error, "Ошибка добавления секции")),
  });

  const addFieldMutation = useMutation({
    mutationFn: (payload: FieldPayload) => addField(selectedVersion?.id ?? "", payload),
    onSuccess: () => {
      message.success("Поле добавлено");
      fieldForm.resetFields();
      refreshVersions();
    },
    onError: (error) => message.error(apiError(error, "Ошибка добавления поля")),
  });

  const publishMutation = useMutation({
    mutationFn: async () => {
      if (!selectedVersion) throw new Error("Версия не выбрана");
      const validation = await validateSchema(selectedVersion.id);
      if (!validation.valid) throw new Error(validation.errors.map((item) => `${item.field ?? "schema"}: ${item.message}`).join("; "));
      return publishDocumentTypeVersion(selectedVersion.id);
    },
    onSuccess: () => {
      message.success("Версия опубликована");
      refreshVersions();
    },
    onError: (error) => message.error(apiError(error, "Ошибка публикации")),
  });

  const onAddField = (values: {
    sectionCode: string;
    code: string;
    name: string;
    type: FieldType;
    required?: boolean;
    readonly?: boolean;
    sortOrder?: number;
    enumOptions?: string;
    precision?: number;
    min?: number;
  }) => {
    const settings =
      values.type === "enum"
        ? { options: (values.enumOptions ?? "").split(",").map((item) => item.trim()).filter(Boolean) }
        : values.type === "money" || values.type === "decimal"
          ? { precision: values.precision ?? 2, min: values.min ?? 0 }
          : {};
    addFieldMutation.mutate({
      sectionCode: values.sectionCode,
      code: values.code,
      name: values.name,
      type: values.type,
      required: Boolean(values.required),
      readonly: Boolean(values.readonly),
      sortOrder: values.sortOrder ?? 10,
      settings,
      validation: {},
    });
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {typesQuery.isError ? <Alert type="error" showIcon message={apiError(typesQuery.error, "Ошибка загрузки типов")} /> : null}
      <Card>
        <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
          <Typography.Title level={4} style={{ margin: 0 }}>Типы документов</Typography.Title>
          <Button type="primary" onClick={() => setCreateOpen(true)}>Создать тип документа</Button>
        </Space>
        <Table<DocumentType>
          loading={typesQuery.isLoading}
          rowKey="id"
          dataSource={typesQuery.data ?? []}
          rowSelection={{ type: "radio", selectedRowKeys: selectedTypeId ? [selectedTypeId] : [], onChange: (keys) => setSelectedTypeId(String(keys[0])) }}
          columns={[
            { title: "Код", dataIndex: "code" },
            { title: "Название", dataIndex: "name" },
            { title: "Системный", dataIndex: "is_system", render: (value: boolean) => <Tag>{value ? "Да" : "Нет"}</Tag> },
            { title: "Активен", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Да" : "Нет"}</Tag> },
            { title: "Создан", dataIndex: "created_at", render: (value: string) => new Date(value).toLocaleString() },
          ]}
        />
      </Card>

      {selectedTypeId ? (
        <Card>
          <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
            <Typography.Title level={4} style={{ margin: 0 }}>Версии формы</Typography.Title>
            <Space>
              <Button onClick={() => createVersionMutation.mutate()} loading={createVersionMutation.isPending}>Создать версию</Button>
              <Button onClick={() => setPreviewOpen(true)} disabled={!selectedVersion}>Предпросмотр формы</Button>
              <Button type="primary" onClick={() => publishMutation.mutate()} disabled={!isDraft} loading={publishMutation.isPending}>Опубликовать</Button>
            </Space>
          </Space>
          <Table
            size="small"
            rowKey="id"
            dataSource={versionsQuery.data ?? []}
            rowSelection={{ type: "radio", selectedRowKeys: selectedVersion?.id ? [selectedVersion.id] : [], onChange: (keys) => setSelectedVersionId(String(keys[0])) }}
            columns={[
              { title: "Версия", dataIndex: "version_number" },
              { title: "Статус", dataIndex: "status", render: (value: string) => <Tag>{value}</Tag> },
              { title: "Опубликована", dataIndex: "published_at", render: (value: string | null) => (value ? new Date(value).toLocaleString() : "-") },
            ]}
          />

          {selectedVersion ? (
            <>
              <Divider />
              {!isDraft ? <Alert type="info" showIcon message="Опубликованные и архивные версии доступны только для просмотра." style={{ marginBottom: 12 }} /> : null}
              <Space align="start" style={{ width: "100%" }} wrap>
                <Form form={sectionForm} layout="vertical" onFinish={(values) => addSectionMutation.mutate(values)} disabled={!isDraft}>
                  <Typography.Text strong>Новая секция</Typography.Text>
                  <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input placeholder="main" /></Form.Item>
                  <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input placeholder="Основные данные" /></Form.Item>
                  <Form.Item name="sortOrder" label="Порядок" initialValue={10}><InputNumber style={{ width: "100%" }} /></Form.Item>
                  <Button htmlType="submit" loading={addSectionMutation.isPending}>Добавить секцию</Button>
                </Form>

                <Form form={fieldForm} layout="vertical" onFinish={onAddField} disabled={!isDraft}>
                  <Typography.Text strong>Новое поле</Typography.Text>
                  <Space align="start" wrap>
                    <Form.Item name="sectionCode" label="Секция" rules={[{ required: true }]}>
                      <Select style={{ width: 180 }} options={selectedVersion.schema_json.sections.map((item) => ({ value: item.code, label: item.name }))} />
                    </Form.Item>
                    <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input style={{ width: 150 }} /></Form.Item>
                    <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input style={{ width: 180 }} /></Form.Item>
                    <Form.Item name="type" label="Тип" initialValue="string" rules={[{ required: true }]}>
                      <Select style={{ width: 145 }} options={fieldTypes.map((item) => ({ value: item, label: item }))} />
                    </Form.Item>
                    <Form.Item name="sortOrder" label="Порядок" initialValue={10}><InputNumber style={{ width: 100 }} /></Form.Item>
                    <Form.Item name="required" valuePropName="checked" label="Обяз."><Checkbox /></Form.Item>
                    <Form.Item name="readonly" valuePropName="checked" label="Readonly"><Checkbox /></Form.Item>
                  </Space>
                  <Space align="start" wrap>
                    <Form.Item name="enumOptions" label="Enum options"><Input style={{ width: 240 }} placeholder="one, two, three" /></Form.Item>
                    <Form.Item name="precision" label="Precision"><InputNumber style={{ width: 120 }} /></Form.Item>
                    <Form.Item name="min" label="Min"><InputNumber style={{ width: 120 }} /></Form.Item>
                    <Form.Item label=" "><Button htmlType="submit" type="primary" loading={addFieldMutation.isPending}>Добавить поле</Button></Form.Item>
                  </Space>
                </Form>
              </Space>

              <Divider />
              {selectedVersion.schema_json.sections.map((section: DocumentSectionSchema) => (
                <Card key={section.code} size="small" title={`${section.sortOrder ?? 0}. ${section.name} (${section.code})`} style={{ marginBottom: 12 }}>
                  <Table<DocumentFieldSchema>
                    size="small"
                    rowKey="code"
                    pagination={false}
                    dataSource={section.fields}
                    columns={[
                      { title: "Код", dataIndex: "code" },
                      { title: "Название", dataIndex: "name" },
                      { title: "Тип", dataIndex: "type" },
                      { title: "Обяз.", dataIndex: "required", render: (value: boolean) => (value ? "Да" : "Нет") },
                      { title: "Действия", render: (_, field) => <Button danger disabled={!isDraft} onClick={() => deleteField(selectedVersion.id, field.code).then(refreshVersions)}>Удалить</Button> },
                    ]}
                  />
                  <Button danger disabled={!isDraft || section.fields.length > 0} onClick={() => deleteSection(selectedVersion.id, section.code).then(refreshVersions)} style={{ marginTop: 8 }}>
                    Удалить пустую секцию
                  </Button>
                </Card>
              ))}
            </>
          ) : null}
        </Card>
      ) : null}

      <Modal title="Создать тип документа" open={createOpen} onCancel={() => setCreateOpen(false)} footer={null}>
        <Form
          form={typeForm}
          layout="vertical"
          onFinish={(values: { code: string; name: string; description?: string; is_system?: boolean; is_active?: boolean }) =>
            createTypeMutation.mutate({ code: values.code, name: values.name, description: values.description ?? null, is_system: Boolean(values.is_system), is_active: values.is_active ?? true })
          }
          initialValues={{ is_active: true, is_system: false }}
        >
          <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input placeholder="PaymentRequest" /></Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Описание"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="is_system" valuePropName="checked"><Checkbox>Системный</Checkbox></Form.Item>
          <Form.Item name="is_active" valuePropName="checked"><Checkbox>Активен</Checkbox></Form.Item>
          <Button htmlType="submit" type="primary" loading={createTypeMutation.isPending}>Создать</Button>
        </Form>
      </Modal>

      <Modal title="Предпросмотр формы" open={previewOpen} onCancel={() => setPreviewOpen(false)} footer={null} width={760}>
        {selectedVersion ? <Form layout="vertical"><DynamicFormRenderer schema={selectedVersion.schema_json} /></Form> : null}
      </Modal>
    </Space>
  );
};
