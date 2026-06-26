import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Checkbox, Form, Input, InputNumber, Select, Space, Table, Tag, Typography, message } from "antd";

import { getDocumentTypes } from "../../entities/document-type";
import { createMatrixRule, deleteMatrixRule, getMatrixRules, getRoutes } from "../../entities/workflow";
import type { ApprovalMatrixRule, MatrixConditionGroup } from "../../entities/workflow";
import { setUserIdHeader } from "../../shared/api/axios";

const operators = ["=", "!=", ">", ">=", "<", "<=", "in", "not_in", "is_empty", "is_not_empty"];

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const parseValue = (operator: string, value?: string) => {
  if (operator === "is_empty" || operator === "is_not_empty") return undefined;
  if (operator === "in" || operator === "not_in") return (value ?? "").split(",").map((item) => item.trim()).filter(Boolean);
  const numeric = Number(value);
  return Number.isNaN(numeric) || value === "" || value == null ? value : numeric;
};

export const ApprovalMatrixBuilderPage = () => {
  const [form] = Form.useForm();
  const rulesQuery = useQuery({ queryKey: ["matrix-rules"], queryFn: getMatrixRules });
  const typesQuery = useQuery({ queryKey: ["document-types"], queryFn: getDocumentTypes });
  const routesQuery = useQuery({ queryKey: ["routes"], queryFn: getRoutes });

  const createMutation = useMutation({
    mutationFn: (payload: { userId: string; body: Omit<ApprovalMatrixRule, "id" | "created_at" | "updated_at"> }) => {
      setUserIdHeader(payload.userId);
      return createMatrixRule(payload.body);
    },
    onSuccess: () => {
      message.success("Правило создано");
      form.resetFields();
      void rulesQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания правила")),
  });

  const deleteMutation = useMutation({
    mutationFn: (payload: { id: string; userId: string }) => {
      setUserIdHeader(payload.userId);
      return deleteMatrixRule(payload.id);
    },
    onSuccess: () => {
      message.success("Правило отключено");
      void rulesQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка удаления правила")),
  });

  const onCreate = (values: {
    user_id: string;
    document_type_id: string;
    route_id: string;
    priority: number;
    name: string;
    is_active?: boolean;
    alwaysTrue?: boolean;
    groupOperator?: "and" | "or";
    conditions?: Array<{ field?: string; operator?: string; value?: string }>;
  }) => {
    const condition_json: MatrixConditionGroup = values.alwaysTrue
      ? { operator: "and", conditions: [] }
      : {
          operator: values.groupOperator ?? "and",
          conditions: (values.conditions ?? [])
            .filter((item) => item.field && item.operator)
            .map((item) => ({ field: String(item.field), operator: String(item.operator), value: parseValue(String(item.operator), item.value) })),
        };
    createMutation.mutate({
      userId: values.user_id,
      body: {
        document_type_id: values.document_type_id,
        route_id: values.route_id,
        priority: values.priority,
        name: values.name,
        condition_json,
        is_active: values.is_active ?? true,
      },
    });
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {rulesQuery.isError ? <Alert type="error" showIcon message={apiError(rulesQuery.error, "Ошибка загрузки правил")} /> : null}
      <Card>
        <Typography.Title level={4}>Матрица согласования</Typography.Title>
        <Form form={form} layout="vertical" onFinish={onCreate} initialValues={{ is_active: true, alwaysTrue: true, groupOperator: "and", conditions: [] }}>
          <Space align="start" wrap>
            <Form.Item name="user_id" label="X-User-Id" rules={[{ required: true }]}><Input style={{ width: 260 }} /></Form.Item>
            <Form.Item name="document_type_id" label="Тип документа" rules={[{ required: true }]}>
              <Select style={{ width: 280 }} options={(typesQuery.data ?? []).map((item) => ({ value: item.id, label: `${item.code} - ${item.name}` }))} />
            </Form.Item>
            <Form.Item name="route_id" label="Маршрут" rules={[{ required: true }]}>
              <Select style={{ width: 280 }} options={(routesQuery.data ?? []).map((item) => ({ value: item.id, label: item.name }))} />
            </Form.Item>
            <Form.Item name="priority" label="Приоритет" rules={[{ required: true }]}><InputNumber style={{ width: 120 }} /></Form.Item>
            <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input style={{ width: 240 }} /></Form.Item>
            <Form.Item name="is_active" valuePropName="checked" label="Активно"><Checkbox /></Form.Item>
          </Space>
          <Space align="start" wrap>
            <Form.Item name="alwaysTrue" valuePropName="checked" label="Always true"><Checkbox /></Form.Item>
            <Form.Item name="groupOperator" label="Группа"><Select style={{ width: 120 }} options={[{ value: "and", label: "and" }, { value: "or", label: "or" }]} /></Form.Item>
          </Space>
          <Form.List name="conditions">
            {(fields, { add, remove }) => (
              <Space direction="vertical" style={{ width: "100%" }}>
                {fields.map((field) => (
                  <Space key={field.key} align="start" wrap>
                    <Form.Item name={[field.name, "field"]} label="Поле"><Input style={{ width: 180 }} placeholder="amount" /></Form.Item>
                    <Form.Item name={[field.name, "operator"]} label="Оператор"><Select style={{ width: 130 }} options={operators.map((item) => ({ value: item, label: item }))} /></Form.Item>
                    <Form.Item name={[field.name, "value"]} label="Значение"><Input style={{ width: 220 }} /></Form.Item>
                    <Form.Item label=" "><Button danger onClick={() => remove(field.name)}>Удалить</Button></Form.Item>
                  </Space>
                ))}
                <Button onClick={() => add({ field: "", operator: ">=", value: "" })}>Добавить условие</Button>
              </Space>
            )}
          </Form.List>
          <Button type="primary" htmlType="submit" loading={createMutation.isPending} style={{ marginTop: 16 }}>Создать правило</Button>
        </Form>
      </Card>
      <Card>
        <Table<ApprovalMatrixRule>
          rowKey="id"
          dataSource={rulesQuery.data ?? []}
          columns={[
            { title: "Название", dataIndex: "name" },
            { title: "Приоритет", dataIndex: "priority" },
            { title: "Активно", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Да" : "Нет"}</Tag> },
            { title: "Действия", render: (_, row) => <Button danger onClick={() => deleteMutation.mutate({ id: row.id, userId: form.getFieldValue("user_id") })}>Soft delete</Button> },
          ]}
        />
      </Card>
    </Space>
  );
};
