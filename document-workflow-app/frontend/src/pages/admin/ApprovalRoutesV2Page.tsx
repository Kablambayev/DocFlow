import { PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Steps, Table, Tag, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";

import { getActiveDocumentTypes } from "../../entities/document-type";
import { getUsers } from "../../entities/user";
import { createRoute, createRouteVersion, getRouteVersions, getRoutes, publishRouteVersion, updateRouteVersion } from "../../entities/workflow";
import type { ApprovalRoute, ApprovalStep } from "../../entities/workflow";
import { setUserIdHeader } from "../../shared/api/axios";

type StepFormItem = {
  order: number;
  name: string;
  type: "sequential" | "parallel";
  resolverType: "specific_user" | "role";
  userId?: string;
  roleCode?: string;
  decisionPolicy: "all" | "any";
  slaHours?: number | null;
};

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const toFormStep = (step: ApprovalStep): StepFormItem => ({
  order: step.order,
  name: step.name,
  type: step.type,
  resolverType: step.approverResolver.type,
  userId: "userId" in step.approverResolver ? step.approverResolver.userId : undefined,
  roleCode: "roleCode" in step.approverResolver ? step.approverResolver.roleCode : undefined,
  decisionPolicy: step.decisionPolicy,
  slaHours: step.slaHours ?? null,
});

const toApiStep = (step: StepFormItem, index: number): ApprovalStep => ({
  order: Number(step.order ?? index + 1),
  name: step.name || "Согласование",
  type: step.type ?? "sequential",
  approverResolver:
    step.resolverType === "role"
      ? { type: "role", roleCode: step.roleCode ?? "" }
      : { type: "specific_user", userId: step.userId ?? "" },
  decisionPolicy: step.decisionPolicy ?? "all",
  slaHours: step.slaHours == null ? null : Number(step.slaHours),
});

export const ApprovalRoutesV2Page = () => {
  const [routeForm] = Form.useForm();
  const [versionForm] = Form.useForm<{ steps: StepFormItem[]; publishUserId?: string }>();
  const [routeModalOpen, setRouteModalOpen] = useState(false);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const routesQuery = useQuery({ queryKey: ["routes"], queryFn: getRoutes });
  const typesQuery = useQuery({ queryKey: ["active-document-types"], queryFn: getActiveDocumentTypes });
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: getUsers });
  const versionsQuery = useQuery({
    queryKey: ["route-versions", selectedRouteId],
    queryFn: () => getRouteVersions(selectedRouteId ?? ""),
    enabled: Boolean(selectedRouteId),
  });

  const selectedVersion = useMemo(
    () => versionsQuery.data?.find((item) => item.id === selectedVersionId) ?? versionsQuery.data?.[0],
    [selectedVersionId, versionsQuery.data],
  );
  const isDraft = selectedVersion?.status === "draft";
  const watchedSteps = Form.useWatch("steps", versionForm) ?? [];

  useEffect(() => {
    if (selectedVersion) {
      versionForm.setFieldsValue({ steps: selectedVersion.route_schema_json.steps.map(toFormStep) });
    }
  }, [selectedVersion, versionForm]);

  const createRouteMutation = useMutation({
    mutationFn: createRoute,
    onSuccess: (route) => {
      message.success("Маршрут создан");
      setRouteModalOpen(false);
      setSelectedRouteId(route.id);
      routeForm.resetFields();
      void routesQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания маршрута")),
  });

  const createVersionMutation = useMutation({
    mutationFn: () =>
      createRouteVersion(selectedRouteId ?? "", {
        route_schema_json: {
          steps: [{ order: 1, name: "Согласование", type: "sequential", approverResolver: { type: "specific_user", userId: "" }, decisionPolicy: "all", slaHours: 24 }],
        },
      }),
    onSuccess: (version) => {
      message.success("Черновик маршрута создан");
      setSelectedVersionId(version.id);
      void versionsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания версии")),
  });

  const saveVersionMutation = useMutation({
    mutationFn: (steps: ApprovalStep[]) => updateRouteVersion(selectedVersion?.id ?? "", { route_schema_json: { steps } }),
    onSuccess: () => {
      message.success("Версия маршрута сохранена");
      void versionsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка сохранения версии")),
  });

  const publishMutation = useMutation({
    mutationFn: (userId: string) => {
      setUserIdHeader(userId);
      return publishRouteVersion(selectedVersion?.id ?? "");
    },
    onSuccess: () => {
      message.success("Версия маршрута опубликована");
      void versionsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка публикации")),
  });

  const onSaveVersion = (values: { steps: StepFormItem[] }) => {
    saveVersionMutation.mutate((values.steps ?? []).map(toApiStep).sort((a, b) => a.order - b.order));
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card>
        {routesQuery.isError ? <Alert type="error" showIcon message={apiError(routesQuery.error, "Ошибка загрузки маршрутов")} style={{ marginBottom: 16 }} /> : null}
        <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
          <Typography.Title level={4} style={{ margin: 0 }}>Маршруты согласования</Typography.Title>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setRouteModalOpen(true)}>Создать маршрут</Button>
        </Space>
        <Table<ApprovalRoute>
          rowKey="id"
          dataSource={routesQuery.data ?? []}
          rowSelection={{ type: "radio", selectedRowKeys: selectedRouteId ? [selectedRouteId] : [], onChange: (keys) => setSelectedRouteId(String(keys[0])) }}
          columns={[
            { title: "Код", dataIndex: "code" },
            { title: "Название", dataIndex: "name" },
            { title: "Тип документа", dataIndex: "document_type_id" },
            { title: "Активен", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Да" : "Нет"}</Tag> },
          ]}
        />
      </Card>

      {selectedRouteId ? (
        <Card>
          <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
            <Typography.Title level={4} style={{ margin: 0 }}>Версии маршрута</Typography.Title>
            <Button onClick={() => createVersionMutation.mutate()} loading={createVersionMutation.isPending}>Создать draft</Button>
          </Space>
          <Table
            size="small"
            rowKey="id"
            dataSource={versionsQuery.data ?? []}
            rowSelection={{ type: "radio", selectedRowKeys: selectedVersion?.id ? [selectedVersion.id] : [], onChange: (keys) => setSelectedVersionId(String(keys[0])) }}
            columns={[
              { title: "Версия", dataIndex: "version_number" },
              { title: "Статус", dataIndex: "status", render: (value: string) => <Tag color={value === "published" ? "green" : value === "draft" ? "blue" : "default"}>{value}</Tag> },
            ]}
          />

          {selectedVersion ? (
            <Form form={versionForm} layout="vertical" onFinish={onSaveVersion} disabled={!isDraft} style={{ marginTop: 16 }}>
              {!isDraft ? <Alert type="info" showIcon message="Published/archived версии доступны только для просмотра." style={{ marginBottom: 12 }} /> : null}
              <Form.List name="steps">
                {(fields, { add, remove }) => (
                  <Space direction="vertical" style={{ width: "100%" }}>
                    {fields.map((field) => (
                      <Card key={field.key} size="small">
                        <Space align="start" wrap>
                          <Form.Item name={[field.name, "order"]} label="Order" rules={[{ required: true }]}><InputNumber style={{ width: 100 }} /></Form.Item>
                          <Form.Item name={[field.name, "name"]} label="Название" rules={[{ required: true }]}><Input style={{ width: 220 }} /></Form.Item>
                          <Form.Item name={[field.name, "type"]} label="Тип"><Select style={{ width: 150 }} options={[{ value: "sequential", label: "sequential" }, { value: "parallel", label: "parallel" }]} /></Form.Item>
                          <Form.Item name={[field.name, "resolverType"]} label="Согласующий"><Select style={{ width: 150 }} options={[{ value: "specific_user", label: "user" }, { value: "role", label: "role" }]} /></Form.Item>
                          <Form.Item name={[field.name, "userId"]} label="User"><Select style={{ width: 280 }} options={(usersQuery.data ?? []).map((user) => ({ value: user.id, label: `${user.full_name} (${user.email})` }))} /></Form.Item>
                          <Form.Item name={[field.name, "roleCode"]} label="Role code"><Input style={{ width: 160 }} /></Form.Item>
                          <Form.Item name={[field.name, "decisionPolicy"]} label="Policy"><Select style={{ width: 120 }} options={[{ value: "all", label: "all" }, { value: "any", label: "any" }]} /></Form.Item>
                          <Form.Item name={[field.name, "slaHours"]} label="SLA"><InputNumber style={{ width: 100 }} /></Form.Item>
                          <Form.Item label=" "><Button danger disabled={!isDraft} onClick={() => remove(field.name)}>Удалить</Button></Form.Item>
                        </Space>
                      </Card>
                    ))}
                    <Button disabled={!isDraft} onClick={() => add({ order: fields.length + 1, name: "Согласование", type: "sequential", resolverType: "specific_user", decisionPolicy: "all", slaHours: 24 })}>Добавить шаг</Button>
                  </Space>
                )}
              </Form.List>
              <Space style={{ marginTop: 16 }}>
                <Button type="primary" htmlType="submit" disabled={!isDraft} loading={saveVersionMutation.isPending}>Сохранить версию</Button>
                <Form.Item name="publishUserId" noStyle><Input placeholder="X-User-Id" style={{ width: 260 }} disabled={false} /></Form.Item>
                <Button disabled={!isDraft} onClick={() => publishMutation.mutate(versionForm.getFieldValue("publishUserId"))} loading={publishMutation.isPending}>Опубликовать</Button>
              </Space>
              <Typography.Title level={5} style={{ marginTop: 16 }}>Preview маршрута</Typography.Title>
              <Steps items={[...watchedSteps].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)).map((step) => ({ title: step.name || "Шаг", description: `${step.decisionPolicy ?? "all"} / ${step.resolverType ?? "user"}` }))} />
            </Form>
          ) : null}
        </Card>
      ) : null}

      <Modal title="Создать маршрут" open={routeModalOpen} onCancel={() => setRouteModalOpen(false)} footer={null}>
        <Form
          form={routeForm}
          layout="vertical"
          onFinish={(values: { document_type_id: string; code: string; name: string; description?: string }) =>
            createRouteMutation.mutate({ document_type_id: values.document_type_id, code: values.code, name: values.name, description: values.description ?? null, is_active: true })
          }
        >
          <Form.Item name="document_type_id" label="Тип документа" rules={[{ required: true }]}>
            <Select options={(typesQuery.data ?? []).map((item) => ({ value: item.id, label: `${item.code} - ${item.name}` }))} />
          </Form.Item>
          <Form.Item name="code" label="Код" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Описание"><Input.TextArea rows={3} /></Form.Item>
          <Button type="primary" htmlType="submit" loading={createRouteMutation.isPending}>Создать</Button>
        </Form>
      </Modal>
    </Space>
  );
};
