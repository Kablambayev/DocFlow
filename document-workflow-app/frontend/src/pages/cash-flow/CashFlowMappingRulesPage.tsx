import { DeleteOutlined, EditOutlined, EyeOutlined, PlayCircleOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Checkbox, Drawer, Form, Input, InputNumber, Select, Space, Table, Tabs, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";

import {
  createCashFlowMappingRule,
  deleteCashFlowMappingRule,
  getCashFlowMappingRule,
  getCashFlowMappingRules,
  testCashFlowMappingRule,
  updateCashFlowMappingRule,
} from "../../entities/cash-flow-mapping";
import type {
  CashFlowMappingRuleField,
  CashFlowMappingRuleListItem,
  CashFlowMappingRulePayload,
  CashFlowMappingTestResult,
} from "../../entities/cash-flow-mapping";
import { Can } from "../../shared/auth/Can";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const sampleJson = `{
  "ref": "1c-guid",
  "number": "000000123",
  "date": "2026-06-29",
  "posted_at": "2026-06-29T10:00:00+05:00",
  "organization": { "external_id": "ORG-001" },
  "counterparty": { "external_id": "CNT-001" },
  "contract": { "external_id": "CTR-ORG1-CNT1-142" },
  "currency": { "external_id": "CUR-KZT" },
  "amount": 1500000,
  "payment_purpose": "Оплата поставщику",
  "comment": "",
  "project": { "code": "ERP" },
  "cash_flow_item": { "external_id": "dds-supplier-payment" }
}`;

const targetFieldOptions = [
  "source_system",
  "source_document_external_id",
  "source_document_type",
  "source_document_type_1c",
  "source_document_number",
  "source_document_date",
  "source_document_posted_at",
  "cash_flow_direction",
  "organization_id",
  "counterparty_id",
  "contract_id",
  "currency_id",
  "amount",
  "payment_purpose",
  "cash_flow_item_id",
  "project_id",
  "cash_flow_operation_type_id",
  "management_comment",
  "allocation_status",
];

const dictionaryOptions = ["organization", "counterparty", "contract", "currency", "project", "cash_flow_operation_type", "cash_flow_item"];
const lookupOptions = ["external_id", "code", "name"];
const mappingTypeOptions = ["path", "constant", "dictionary_lookup", "default"];

type DrawerMode = "create" | "edit" | "view";

const emptyRule = (): CashFlowMappingRulePayload => ({
  name: "",
  source_system: "1C",
  source_document_type_1c: "",
  source_document_type_code: "",
  cash_flow_direction: "Outflow",
  target_document_type_code: "CashFlowAllocation",
  is_active: true,
  priority: 100,
  description: "",
  fields: [],
});

const normalizeFieldsForApi = (fields: CashFlowMappingRuleField[]) =>
  fields.map((field) => ({
    ...field,
    id: field.id && !field.id.startsWith("tmp-") ? field.id : undefined,
  }));

const statusColor = (status: string) =>
  ({
    mapped: "green",
    missing: "orange",
    error: "red",
    defaulted: "blue",
    constant: "purple",
  })[status] ?? "default";

export const CashFlowMappingRulesPage = () => {
  const [filterDocument, setFilterDocument] = useState<string>("");
  const [filterDirection, setFilterDirection] = useState<string | undefined>();
  const [filterActive, setFilterActive] = useState<boolean | undefined>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<DrawerMode>("create");
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [editingFieldId, setEditingFieldId] = useState<string | undefined>();
  const [testJson, setTestJson] = useState(sampleJson);
  const [testResult, setTestResult] = useState<CashFlowMappingTestResult | null>(null);
  const [ruleForm] = Form.useForm<CashFlowMappingRulePayload>();
  const [fieldForm] = Form.useForm<CashFlowMappingRuleField>();

  const rulesQuery = useQuery({
    queryKey: ["cash-flow-mapping-rules", filterDocument, filterDirection, filterActive],
    queryFn: () =>
      getCashFlowMappingRules({
        source_document_type_1c: filterDocument || undefined,
        cash_flow_direction: filterDirection,
        is_active: filterActive,
      }),
  });

  const ruleQuery = useQuery({
    queryKey: ["cash-flow-mapping-rule", selectedRuleId],
    queryFn: () => getCashFlowMappingRule(selectedRuleId as string),
    enabled: Boolean(selectedRuleId),
  });

  useEffect(() => {
    if (!ruleQuery.data) return;
    ruleForm.setFieldsValue(ruleQuery.data);
  }, [ruleForm, ruleQuery.data]);

  const createMutation = useMutation({
    mutationFn: createCashFlowMappingRule,
    onSuccess: (data) => {
      message.success("Правило создано");
      setSelectedRuleId(data.id);
      setDrawerMode("edit");
      void rulesQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания правила")),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<CashFlowMappingRulePayload> }) => updateCashFlowMappingRule(id, payload),
    onSuccess: () => {
      message.success("Правило обновлено");
      void ruleQuery.refetch();
      void rulesQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления правила")),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCashFlowMappingRule,
    onSuccess: () => {
      message.success("Правило удалено");
      setDrawerOpen(false);
      setSelectedRuleId(null);
      void rulesQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка удаления правила")),
  });

  const testMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => testCashFlowMappingRule(id, payload),
    onSuccess: (data) => setTestResult(data),
    onError: (error) => message.error(apiError(error, "Ошибка теста маппинга")),
  });

  const openCreate = () => {
    setDrawerMode("create");
    setSelectedRuleId(null);
    setDrawerOpen(true);
    setEditingFieldId(undefined);
    setTestJson(sampleJson);
    setTestResult(null);
    ruleForm.setFieldsValue(emptyRule());
    fieldForm.setFieldsValue({ mapping_type: "path", sort_order: 100, is_required: false });
  };

  const openExisting = (ruleId: string, mode: DrawerMode) => {
    setDrawerMode(mode);
    setSelectedRuleId(ruleId);
    setDrawerOpen(true);
    setEditingFieldId(undefined);
    setTestResult(null);
    fieldForm.setFieldsValue({ mapping_type: "path", sort_order: 100, is_required: false });
  };

  const fields = Form.useWatch("fields", ruleForm) ?? [];
  const readonly = drawerMode === "view";

  const saveField = async () => {
    const value = await fieldForm.validateFields();
    const nextFields = [...fields];
    if (editingFieldId) {
      const index = nextFields.findIndex((item) => item.id === editingFieldId);
      if (index >= 0) {
        nextFields[index] = { ...nextFields[index], ...value };
      }
    } else {
      nextFields.push({ ...value, id: `tmp-${Date.now()}` });
    }
    ruleForm.setFieldValue(
      "fields",
      nextFields.sort((left, right) => left.sort_order - right.sort_order),
    );
    setEditingFieldId(undefined);
    fieldForm.setFieldsValue({ mapping_type: "path", sort_order: 100, is_required: false });
  };

  const persistRule = async () => {
    const payload = await ruleForm.validateFields();
    const normalizedPayload = { ...payload, fields: normalizeFieldsForApi(payload.fields ?? []) };
    if (drawerMode === "create") {
      createMutation.mutate(normalizedPayload);
      return;
    }
    if (selectedRuleId) {
      updateMutation.mutate({ id: selectedRuleId, payload: normalizedPayload });
    }
  };

  const runTest = async () => {
    const payload = await ruleForm.validateFields();
    const normalizedPayload = { ...payload, fields: normalizeFieldsForApi(payload.fields ?? []) };
    let parsedJson: Record<string, unknown>;
    try {
      parsedJson = JSON.parse(testJson) as Record<string, unknown>;
    } catch {
      message.error("Невалидный JSON источника");
      return;
    }
    if (drawerMode === "create") {
      createMutation.mutate(normalizedPayload, {
        onSuccess: (data) => testMutation.mutate({ id: data.id, payload: parsedJson }),
      });
      return;
    }
    if (selectedRuleId) {
      updateMutation.mutate(
        { id: selectedRuleId, payload: normalizedPayload },
        { onSuccess: () => testMutation.mutate({ id: selectedRuleId, payload: parsedJson }) },
      );
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div>
        <Typography.Title level={4} style={{ margin: 0 }}>Сопоставление БДДС</Typography.Title>
        <Typography.Text type="secondary">Конструктор правил преобразования JSON из 1С в документ «Разноска БДДС».</Typography.Text>
      </div>

      <Card size="small">
        <Space wrap>
          <Input placeholder="Документ 1С" style={{ width: 280 }} value={filterDocument} onChange={(event) => setFilterDocument(event.target.value)} />
          <Select
            allowClear
            placeholder="Направление"
            style={{ width: 180 }}
            value={filterDirection}
            onChange={(value) => setFilterDirection(value)}
            options={[{ value: "Inflow", label: "Inflow" }, { value: "Outflow", label: "Outflow" }]}
          />
          <Select
            allowClear
            placeholder="Активность"
            style={{ width: 180 }}
            value={filterActive}
            onChange={(value) => setFilterActive(value)}
            options={[{ value: true, label: "Активные" }, { value: false, label: "Неактивные" }]}
          />
          <Can permission="cash_flow.mapping.manage">
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Создать правило</Button>
          </Can>
        </Space>
      </Card>

      {rulesQuery.isError ? <Alert type="error" showIcon message={apiError(rulesQuery.error, "Не удалось загрузить правила")} /> : null}

      <Card size="small">
        <Table<CashFlowMappingRuleListItem>
          rowKey="id"
          loading={rulesQuery.isLoading}
          dataSource={rulesQuery.data ?? []}
          columns={[
            { title: "Название", dataIndex: "name" },
            { title: "Документ 1С", dataIndex: "source_document_type_1c" },
            { title: "Код документа", dataIndex: "source_document_type_code" },
            { title: "Направление", dataIndex: "cash_flow_direction" },
            { title: "Целевой документ", dataIndex: "target_document_type_code" },
            { title: "Приоритет", dataIndex: "priority" },
            { title: "Активно", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Да" : "Нет"}</Tag> },
            { title: "Поля", dataIndex: "fields_count" },
            {
              title: "Действия",
              render: (_, row) => (
                <Space>
                  <Button icon={<EyeOutlined />} onClick={() => openExisting(row.id, "view")}>Открыть</Button>
                  <Can permission="cash_flow.mapping.manage">
                    <Button icon={<EditOutlined />} onClick={() => openExisting(row.id, "edit")}>Редактировать</Button>
                    <Button icon={<PlayCircleOutlined />} onClick={() => openExisting(row.id, "edit")}>Тест</Button>
                    <Button danger icon={<DeleteOutlined />} onClick={() => deleteMutation.mutate(row.id)}>Удалить</Button>
                  </Can>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Drawer
        title={drawerMode === "create" ? "Новое правило" : drawerMode === "edit" ? "Редактирование правила" : "Просмотр правила"}
        width={960}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={!readonly ? <Button type="primary" onClick={() => void persistRule()} loading={createMutation.isPending || updateMutation.isPending}>Сохранить</Button> : null}
      >
        <Form form={ruleForm} layout="vertical" initialValues={emptyRule()}>
          <Tabs
            items={[
              {
                key: "main",
                label: "Основное",
                children: (
                  <Space direction="vertical" size={12} style={{ width: "100%" }}>
                    <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input disabled={readonly} /></Form.Item>
                    <Form.Item name="source_system" label="Source system" rules={[{ required: true }]}><Input disabled={readonly} /></Form.Item>
                    <Form.Item name="source_document_type_1c" label="Документ 1С" rules={[{ required: true }]}><Input disabled={readonly} /></Form.Item>
                    <Form.Item name="source_document_type_code" label="Код документа" rules={[{ required: true }]}><Input disabled={readonly} /></Form.Item>
                    <Form.Item name="cash_flow_direction" label="Направление" rules={[{ required: true }]}>
                      <Select disabled={readonly} options={[{ value: "Inflow", label: "Inflow" }, { value: "Outflow", label: "Outflow" }]} />
                    </Form.Item>
                    <Form.Item name="target_document_type_code" label="Целевой документ" rules={[{ required: true }]}><Input disabled={readonly} /></Form.Item>
                    <Form.Item name="priority" label="Приоритет" rules={[{ required: true }]}><InputNumber disabled={readonly} style={{ width: "100%" }} /></Form.Item>
                    <Form.Item name="description" label="Описание"><Input.TextArea rows={3} disabled={readonly} /></Form.Item>
                    <Form.Item name="is_active" valuePropName="checked"><Checkbox disabled={readonly}>Правило активно</Checkbox></Form.Item>
                  </Space>
                ),
              },
              {
                key: "fields",
                label: "Поля сопоставления",
                children: (
                  <Space direction="vertical" size={16} style={{ width: "100%" }}>
                    {!readonly ? (
                      <Card size="small" title={editingFieldId ? "Редактирование поля" : "Добавление поля"}>
                        <Form form={fieldForm} layout="vertical" initialValues={{ mapping_type: "path", sort_order: 100, is_required: false }}>
                          <Form.Item name="target_field" label="Поле Разноски" rules={[{ required: true }]}>
                            <Select options={targetFieldOptions.map((value) => ({ value, label: value }))} />
                          </Form.Item>
                          <Form.Item name="mapping_type" label="Тип маппинга" rules={[{ required: true }]}>
                            <Select options={mappingTypeOptions.map((value) => ({ value, label: value }))} />
                          </Form.Item>
                          <Form.Item noStyle shouldUpdate>
                            {() => {
                              const mappingType = fieldForm.getFieldValue("mapping_type");
                              return (
                                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                                  {(mappingType === "path" || mappingType === "dictionary_lookup" || mappingType === "default") ? (
                                    <Form.Item name="source_path" label="JSON path">
                                      <Input />
                                    </Form.Item>
                                  ) : null}
                                  {mappingType === "constant" ? (
                                    <Form.Item name="constant_value" label="Константа">
                                      <Input />
                                    </Form.Item>
                                  ) : null}
                                  {mappingType === "default" ? (
                                    <Form.Item name="default_value" label="Default">
                                      <Input />
                                    </Form.Item>
                                  ) : null}
                                  {mappingType === "dictionary_lookup" ? (
                                    <>
                                      <Form.Item name="dictionary_type" label="Справочник">
                                        <Select options={dictionaryOptions.map((value) => ({ value, label: value }))} />
                                      </Form.Item>
                                      <Form.Item name="lookup_by" label="Поиск по">
                                        <Select options={lookupOptions.map((value) => ({ value, label: value }))} />
                                      </Form.Item>
                                    </>
                                  ) : null}
                                </Space>
                              );
                            }}
                          </Form.Item>
                          <Form.Item name="sort_order" label="Порядок"><InputNumber style={{ width: "100%" }} /></Form.Item>
                          <Form.Item name="is_required" valuePropName="checked"><Checkbox>Обязательное поле</Checkbox></Form.Item>
                          <Space>
                            <Button type="primary" onClick={() => void saveField()}>Сохранить поле</Button>
                            <Button onClick={() => { setEditingFieldId(undefined); fieldForm.setFieldsValue({ mapping_type: "path", sort_order: 100, is_required: false }); }}>Сбросить</Button>
                          </Space>
                        </Form>
                      </Card>
                    ) : null}
                    <Table<CashFlowMappingRuleField>
                      rowKey={(row) => row.id ?? `${row.target_field}-${row.sort_order}`}
                      dataSource={fields}
                      pagination={false}
                      columns={[
                        { title: "Поле Разноски", dataIndex: "target_field" },
                        { title: "Тип", dataIndex: "mapping_type" },
                        { title: "JSON path", dataIndex: "source_path" },
                        { title: "Константа", dataIndex: "constant_value", render: (value) => value == null ? "-" : JSON.stringify(value) },
                        { title: "Default", dataIndex: "default_value", render: (value) => value == null ? "-" : JSON.stringify(value) },
                        { title: "Справочник", dataIndex: "dictionary_type" },
                        { title: "Поиск по", dataIndex: "lookup_by" },
                        { title: "Обязательное", dataIndex: "is_required", render: (value: boolean) => value ? "Да" : "Нет" },
                        { title: "Порядок", dataIndex: "sort_order" },
                        {
                          title: "Действия",
                          render: (_, row) => readonly ? null : (
                            <Space>
                              <Button onClick={() => { setEditingFieldId(row.id); fieldForm.setFieldsValue(row); }}>Редактировать</Button>
                              <Button danger onClick={() => ruleForm.setFieldValue("fields", fields.filter((item) => item.id !== row.id))}>Удалить</Button>
                            </Space>
                          ),
                        },
                      ]}
                    />
                  </Space>
                ),
              },
              {
                key: "test",
                label: "Тест маппинга",
                children: (
                  <Space direction="vertical" size={16} style={{ width: "100%" }}>
                    <Input.TextArea rows={14} value={testJson} onChange={(event) => setTestJson(event.target.value)} />
                    <Can permission="cash_flow.mapping.manage">
                      <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => void runTest()} loading={testMutation.isPending}>Проверить сопоставление</Button>
                    </Can>
                    {testResult ? (
                      <Card size="small">
                        <Space direction="vertical" size={12} style={{ width: "100%" }}>
                          <Alert type={testResult.status === "Completed" ? "success" : testResult.status === "NeedsEnrichment" ? "warning" : "error"} showIcon message={`Статус: ${testResult.status}`} />
                          <Typography.Text>
                            Missing required fields: {testResult.missing_required_fields.length ? testResult.missing_required_fields.join(", ") : "нет"}
                          </Typography.Text>
                          <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{JSON.stringify(testResult.mapped_data, null, 2)}</pre>
                          <Table
                            rowKey={(row) => `${row.target_field}-${row.mapping_type}`}
                            dataSource={testResult.field_results}
                            pagination={false}
                            columns={[
                              { title: "Поле", dataIndex: "target_field" },
                              { title: "Тип", dataIndex: "mapping_type" },
                              { title: "Источник", dataIndex: "source_path" },
                              { title: "Source value", dataIndex: "source_value", render: (value) => value == null ? "-" : JSON.stringify(value) },
                              { title: "Mapped value", dataIndex: "mapped_value", render: (value) => value == null ? "-" : JSON.stringify(value) },
                              { title: "Статус", dataIndex: "status", render: (value: string) => <Tag color={statusColor(value)}>{value}</Tag> },
                              { title: "Сообщение", dataIndex: "message" },
                            ]}
                          />
                        </Space>
                      </Card>
                    ) : null}
                  </Space>
                ),
              },
            ]}
          />
        </Form>
      </Drawer>
    </Space>
  );
};
