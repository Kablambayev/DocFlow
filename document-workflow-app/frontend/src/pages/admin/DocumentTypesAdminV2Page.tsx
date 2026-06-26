import { EditOutlined, EyeOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
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
  updateField,
  updateSection,
  validateSchema,
} from "../../entities/document-type";
import type {
  DocumentFieldSchema,
  DocumentSectionSchema,
  DocumentType,
  DocumentTypeVersion,
  FieldPayload,
  FieldType,
  SectionPayload,
} from "../../entities/document-type";
import { DynamicFormRenderer } from "../../shared/ui/DynamicFormRenderer";

const fieldTypes: FieldType[] = ["string", "text", "integer", "decimal", "money", "date", "datetime", "boolean", "enum", "reference", "file", "table"];
const defaultSchema = { sections: [{ code: "main", name: "Основные данные", sortOrder: 10, fields: [] }] };

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const versionStatus = (status?: string) => {
  const value = (status ?? "").toLowerCase();
  if (value === "draft") return { label: "Draft", color: "blue" };
  if (value === "published") return { label: "Published", color: "green" };
  if (value === "archived") return { label: "Archived", color: "default" };
  return { label: status ?? "-", color: "default" };
};

const parseJson = (value: string | undefined, fallback: Record<string, unknown>) => {
  if (!value?.trim()) return fallback;
  return JSON.parse(value) as Record<string, unknown>;
};

const optionsToText = (settings?: Record<string, unknown>) => {
  const options = Array.isArray(settings?.options) ? settings.options : [];
  return options.map((item) => String(item)).join("\n");
};

export const DocumentTypesAdminV2Page = () => {
  const [typeForm] = Form.useForm();
  const [sectionForm] = Form.useForm<SectionPayload>();
  const [fieldForm] = Form.useForm<
    Omit<FieldPayload, "settings" | "validation"> & { enumOptionsText?: string; settingsJson?: string; validationJson?: string }
  >();
  const [typeModalOpen, setTypeModalOpen] = useState(false);
  const [sectionModalOpen, setSectionModalOpen] = useState(false);
  const [fieldModalOpen, setFieldModalOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [editingSectionCode, setEditingSectionCode] = useState<string | null>(null);
  const [editingFieldCode, setEditingFieldCode] = useState<string | null>(null);

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
  const selectedStatus = versionStatus(selectedVersion?.status);
  const isDraft = selectedStatus.label === "Draft";
  const refreshVersions = () => void versionsQuery.refetch();

  const createTypeMutation = useMutation({
    mutationFn: createDocumentType,
    onSuccess: (created) => {
      message.success("Тип документа создан");
      setTypeModalOpen(false);
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

  const saveSectionMutation = useMutation({
    mutationFn: (payload: SectionPayload) =>
      editingSectionCode ? updateSection(selectedVersion?.id ?? "", editingSectionCode, payload) : addSection(selectedVersion?.id ?? "", payload),
    onSuccess: () => {
      message.success(editingSectionCode ? "Секция обновлена" : "Секция добавлена");
      setSectionModalOpen(false);
      setEditingSectionCode(null);
      sectionForm.resetFields();
      refreshVersions();
    },
    onError: (error) => message.error(apiError(error, "Ошибка сохранения секции")),
  });

  const saveFieldMutation = useMutation({
    mutationFn: (payload: FieldPayload) =>
      editingFieldCode ? updateField(selectedVersion?.id ?? "", editingFieldCode, payload) : addField(selectedVersion?.id ?? "", payload),
    onSuccess: () => {
      message.success(editingFieldCode ? "Поле обновлено" : "Поле добавлено");
      setFieldModalOpen(false);
      setEditingFieldCode(null);
      fieldForm.resetFields();
      refreshVersions();
    },
    onError: (error) => message.error(apiError(error, "Ошибка сохранения поля")),
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

  const openSectionModal = (section?: DocumentSectionSchema) => {
    setEditingSectionCode(section?.code ?? null);
    sectionForm.setFieldsValue(section ? { code: section.code, name: section.name, sortOrder: section.sortOrder ?? 10 } : { code: "", name: "", sortOrder: 10 });
    setSectionModalOpen(true);
  };

  const openFieldModal = (sectionCode: string, field?: DocumentFieldSchema) => {
    setEditingFieldCode(field?.code ?? null);
    const settings = field?.settings ?? (field?.type === "money" ? { precision: 2, min: 0 } : {});
    fieldForm.setFieldsValue({
      sectionCode,
      code: field?.code ?? "",
      name: field?.name ?? "",
      type: field?.type ?? "string",
      required: field?.required ?? false,
      readonly: field?.readonly ?? false,
      sortOrder: field?.sortOrder ?? 10,
      enumOptionsText: optionsToText(settings),
      settingsJson: JSON.stringify(settings, null, 2),
      validationJson: JSON.stringify(field?.validation ?? {}, null, 2),
    });
    setFieldModalOpen(true);
  };

  const onSaveField = (values: Omit<FieldPayload, "settings" | "validation"> & { enumOptionsText?: string; settingsJson?: string; validationJson?: string }) => {
    try {
      let settings: Record<string, unknown> = parseJson(values.settingsJson, {});
      if (values.type === "enum") {
        settings = { ...settings, options: (values.enumOptionsText ?? "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean) };
      }
      if (values.type === "money" && Object.keys(settings).length === 0) {
        settings = { precision: 2, min: 0 };
      }
      const validation = parseJson(values.validationJson, {});
      saveFieldMutation.mutate({
        sectionCode: values.sectionCode,
        code: values.code,
        name: values.name,
        type: values.type,
        required: Boolean(values.required),
        readonly: Boolean(values.readonly),
        sortOrder: values.sortOrder ?? 10,
        settings,
        validation,
      });
    } catch {
      message.error("Некорректный JSON в settings или validation");
    }
  };

  const deleteEmptySection = (version: DocumentTypeVersion, section: DocumentSectionSchema) => {
    if (section.fields.length > 0) {
      message.warning("Нельзя удалить секцию с полями");
      return;
    }
    void deleteSection(version.id, section.code).then(refreshVersions).catch((error) => message.error(apiError(error, "Ошибка удаления секции")));
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card>
        {typesQuery.isError ? <Alert type="error" showIcon message={apiError(typesQuery.error, "Ошибка загрузки типов")} style={{ marginBottom: 16 }} /> : null}
        <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
          <Typography.Title level={4} style={{ margin: 0 }}>Типы документов</Typography.Title>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setTypeModalOpen(true)}>Создать тип</Button>
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
          ]}
        />
      </Card>

      {selectedTypeId ? (
        <Card>
          <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
            <Typography.Title level={4} style={{ margin: 0 }}>Версии формы</Typography.Title>
            <Space>
              <Button onClick={() => createVersionMutation.mutate()} loading={createVersionMutation.isPending}>Создать draft</Button>
              <Button icon={<EyeOutlined />} onClick={() => setPreviewOpen(true)} disabled={!selectedVersion}>Preview</Button>
              <Button type="primary" onClick={() => publishMutation.mutate()} disabled={!isDraft} loading={publishMutation.isPending}>Publish</Button>
            </Space>
          </Space>
          <Table<DocumentTypeVersion>
            size="small"
            rowKey="id"
            dataSource={versionsQuery.data ?? []}
            rowSelection={{ type: "radio", selectedRowKeys: selectedVersion?.id ? [selectedVersion.id] : [], onChange: (keys) => setSelectedVersionId(String(keys[0])) }}
            columns={[
              { title: "Версия", dataIndex: "version_number" },
              { title: "Статус", dataIndex: "status", render: (status: string) => { const meta = versionStatus(status); return <Tag color={meta.color}>{meta.label}</Tag>; } },
              { title: "Опубликована", dataIndex: "published_at", render: (value: string | null) => (value ? new Date(value).toLocaleString() : "-") },
            ]}
          />

          {selectedVersion ? (
            <Space direction="vertical" size={12} style={{ width: "100%", marginTop: 16 }}>
              {!isDraft ? <Alert type="info" showIcon message={`${selectedStatus.label} версии доступны только для просмотра.`} /> : null}
              <Space style={{ width: "100%", justifyContent: "space-between" }}>
                <Typography.Title level={5} style={{ margin: 0 }}>Секции и поля</Typography.Title>
                <Button disabled={!isDraft} onClick={() => openSectionModal()}>Добавить секцию</Button>
              </Space>
              {selectedVersion.schema_json.sections.length === 0 ? <Alert type="warning" showIcon message="В форме пока нет секций." /> : null}
              {selectedVersion.schema_json.sections.map((section) => (
                <Card
                  key={section.code}
                  size="small"
                  title={`${section.sortOrder ?? 0}. ${section.name} (${section.code})`}
                  extra={
                    <Space>
                      <Button disabled={!isDraft} icon={<EditOutlined />} onClick={() => openSectionModal(section)}>Редактировать</Button>
                      <Button disabled={!isDraft} onClick={() => openFieldModal(section.code)}>Добавить поле</Button>
                      <Button danger disabled={!isDraft || section.fields.length > 0} onClick={() => deleteEmptySection(selectedVersion, section)}>Удалить</Button>
                    </Space>
                  }
                >
                  <Table<DocumentFieldSchema>
                    size="small"
                    rowKey="code"
                    pagination={false}
                    dataSource={[...section.fields].sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0))}
                    columns={[
                      { title: "Порядок", dataIndex: "sortOrder" },
                      { title: "Код", dataIndex: "code" },
                      { title: "Название", dataIndex: "name" },
                      { title: "Тип", dataIndex: "type" },
                      { title: "Обяз.", dataIndex: "required", render: (value: boolean) => (value ? "Да" : "Нет") },
                      { title: "Readonly", dataIndex: "readonly", render: (value: boolean) => (value ? "Да" : "Нет") },
                      {
                        title: "Действия",
                        render: (_, field) => (
                          <Space>
                            <Button disabled={!isDraft} onClick={() => openFieldModal(section.code, field)}>Редактировать</Button>
                            <Button danger disabled={!isDraft} onClick={() => deleteField(selectedVersion.id, field.code).then(refreshVersions).catch((error) => message.error(apiError(error, "Ошибка удаления поля")))}>Удалить</Button>
                          </Space>
                        ),
                      },
                    ]}
                  />
                </Card>
              ))}
            </Space>
          ) : null}
        </Card>
      ) : null}

      <Modal title="Создать тип документа" open={typeModalOpen} onCancel={() => setTypeModalOpen(false)} footer={null}>
        <Form form={typeForm} layout="vertical" initialValues={{ is_system: false, is_active: true }} onFinish={(values) => createTypeMutation.mutate(values)}>
          <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Описание"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="is_system" valuePropName="checked"><Checkbox>Системный</Checkbox></Form.Item>
          <Form.Item name="is_active" valuePropName="checked"><Checkbox>Активен</Checkbox></Form.Item>
          <Button type="primary" htmlType="submit" loading={createTypeMutation.isPending}>Создать</Button>
        </Form>
      </Modal>

      <Modal title={editingSectionCode ? "Редактировать секцию" : "Добавить секцию"} open={sectionModalOpen} onCancel={() => setSectionModalOpen(false)} footer={null}>
        <Form form={sectionForm} layout="vertical" onFinish={(values) => saveSectionMutation.mutate(values)}>
          <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="sortOrder" label="Sort order" rules={[{ required: true }]}><InputNumber style={{ width: "100%" }} /></Form.Item>
          <Button type="primary" htmlType="submit" loading={saveSectionMutation.isPending}>Сохранить</Button>
        </Form>
      </Modal>

      <Modal title={editingFieldCode ? "Редактировать поле" : "Добавить поле"} open={fieldModalOpen} onCancel={() => setFieldModalOpen(false)} footer={null} width={760}>
        <Form form={fieldForm} layout="vertical" onFinish={onSaveField}>
          <Space align="start" wrap>
            <Form.Item name="sectionCode" label="Секция" rules={[{ required: true }]}>
              <Select style={{ width: 200 }} options={(selectedVersion?.schema_json.sections ?? []).map((section) => ({ value: section.code, label: section.name }))} />
            </Form.Item>
            <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input style={{ width: 160 }} /></Form.Item>
            <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input style={{ width: 220 }} /></Form.Item>
            <Form.Item name="type" label="Тип" rules={[{ required: true }]}><Select style={{ width: 160 }} options={fieldTypes.map((item) => ({ value: item, label: item }))} /></Form.Item>
            <Form.Item name="sortOrder" label="Sort order" rules={[{ required: true }]}><InputNumber style={{ width: 120 }} /></Form.Item>
          </Space>
          <Space align="start" wrap>
            <Form.Item name="required" valuePropName="checked"><Checkbox>Required</Checkbox></Form.Item>
            <Form.Item name="readonly" valuePropName="checked"><Checkbox>Readonly</Checkbox></Form.Item>
          </Space>
          <Form.Item name="enumOptionsText" label="Enum options (one value per line)">
            <Input.TextArea rows={4} placeholder={"new\napproved\nrejected"} />
          </Form.Item>
          <Form.Item name="settingsJson" label="Advanced settings JSON">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="validationJson" label="Advanced validation JSON">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={saveFieldMutation.isPending}>Сохранить</Button>
        </Form>
      </Modal>

      <Modal title="Preview формы" open={previewOpen} onCancel={() => setPreviewOpen(false)} footer={null} width={760}>
        {selectedVersion?.schema_json?.sections ? (
          <Form layout="vertical">
            <DynamicFormRenderer schema={selectedVersion.schema_json} />
          </Form>
        ) : (
          <Alert type="warning" showIcon message="Схема формы пуста или недоступна." />
        )}
      </Modal>
    </Space>
  );
};
