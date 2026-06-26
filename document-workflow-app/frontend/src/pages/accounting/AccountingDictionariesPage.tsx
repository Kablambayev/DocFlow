import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Typography, message } from "antd";
import { useMemo, useState } from "react";

import {
  createCashFlowOperationType,
  createProject,
  deleteCashFlowOperationType,
  deleteProject,
  getCashFlowOperationTypes,
  getCounterparties,
  getCounterpartyContracts,
  getCurrencies,
  getExpenseItems,
  getOrganizations,
  getProjects,
  updateCashFlowOperationType,
  updateProject,
} from "../../entities/accounting";
import type { AccountingDictionaryItem, CounterpartyContractItem } from "../../entities/accounting";
import { Can } from "../../shared/auth/Can";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const DictionaryTable = ({
  title,
  data,
  loading,
  showSource = false,
}: {
  title: string;
  data: AccountingDictionaryItem[];
  loading: boolean;
  showSource?: boolean;
}) => (
  <Card size="small" title={title}>
    <Table
      rowKey="id"
      loading={loading}
      dataSource={data}
      pagination={false}
      columns={[
        { title: "Code", dataIndex: "code" },
        { title: "Name", dataIndex: "name" },
        { title: "Full name", dataIndex: "full_name" },
        { title: "Active", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Yes" : "No"}</Tag> },
        ...(showSource
          ? [
              { title: "Source", dataIndex: "source_system" },
              { title: "Synced", dataIndex: "synced_at", render: (value: string | null | undefined) => value ?? "-" },
            ]
          : []),
      ]}
    />
  </Card>
);

export const AccountingDictionariesPage = () => {
  const [operationModalOpen, setOperationModalOpen] = useState(false);
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [editingOperation, setEditingOperation] = useState<AccountingDictionaryItem | null>(null);
  const [editingProject, setEditingProject] = useState<AccountingDictionaryItem | null>(null);
  const [operationForm] = Form.useForm();
  const [projectForm] = Form.useForm();
  const [contractFilterForm] = Form.useForm();

  const organizationsQuery = useQuery({ queryKey: ["accounting", "organizations"], queryFn: () => getOrganizations({ is_active: true, limit: 100 }) });
  const counterpartiesQuery = useQuery({ queryKey: ["accounting", "counterparties"], queryFn: () => getCounterparties({ is_active: true, limit: 100 }) });
  const currenciesQuery = useQuery({ queryKey: ["accounting", "currencies"], queryFn: () => getCurrencies({ is_active: true, limit: 100 }) });
  const expenseItemsQuery = useQuery({ queryKey: ["accounting", "expense-items"], queryFn: () => getExpenseItems({ is_active: true, limit: 100 }) });
  const operationsQuery = useQuery({ queryKey: ["accounting", "cash-flow-operation-types"], queryFn: () => getCashFlowOperationTypes({ limit: 100 }) });
  const projectsQuery = useQuery({ queryKey: ["accounting", "projects"], queryFn: () => getProjects({ limit: 100 }) });

  const organizationId = Form.useWatch("organization_id", contractFilterForm);
  const counterpartyId = Form.useWatch("counterparty_id", contractFilterForm);
  const contractsQuery = useQuery({
    queryKey: ["accounting", "contracts", organizationId, counterpartyId],
    queryFn: () => getCounterpartyContracts({ organization_id: organizationId, counterparty_id: counterpartyId, is_active: true, limit: 100 }),
    enabled: Boolean(organizationId || counterpartyId),
  });

  const operationsRefetch = operationsQuery.refetch;
  const projectsRefetch = projectsQuery.refetch;

  const createOperationMutation = useMutation({
    mutationFn: createCashFlowOperationType,
    onSuccess: () => {
      message.success("Вид операции создан");
      setOperationModalOpen(false);
      operationForm.resetFields();
      void operationsRefetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания вида операции")),
  });

  const updateOperationMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updateCashFlowOperationType(id, payload),
    onSuccess: () => {
      message.success("Вид операции обновлен");
      setOperationModalOpen(false);
      setEditingOperation(null);
      operationForm.resetFields();
      void operationsRefetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления вида операции")),
  });

  const deactivateOperationMutation = useMutation({
    mutationFn: deleteCashFlowOperationType,
    onSuccess: () => {
      message.success("Вид операции деактивирован");
      void operationsRefetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка деактивации вида операции")),
  });

  const createProjectMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      message.success("Проект создан");
      setProjectModalOpen(false);
      projectForm.resetFields();
      void projectsRefetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания проекта")),
  });

  const updateProjectMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updateProject(id, payload),
    onSuccess: () => {
      message.success("Проект обновлен");
      setProjectModalOpen(false);
      setEditingProject(null);
      projectForm.resetFields();
      void projectsRefetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления проекта")),
  });

  const deactivateProjectMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      message.success("Проект деактивирован");
      void projectsRefetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка деактивации проекта")),
  });

  const contractColumns = useMemo(
    () => [
      { title: "Name", dataIndex: "name" },
      { title: "Number", dataIndex: "number" },
      { title: "Org", dataIndex: "organization_id" },
      { title: "Counterparty", dataIndex: "counterparty_id" },
      { title: "Currency", dataIndex: "currency_id" },
      { title: "Source", dataIndex: "source_system" },
      { title: "Synced", dataIndex: "synced_at", render: (value: string | null | undefined) => value ?? "-" },
      { title: "Active", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Yes" : "No"}</Tag> },
    ],
    [],
  );

  const operationsData = operationsQuery.data ?? [];
  const projectsData = projectsQuery.data ?? [];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Typography.Title level={4} style={{ margin: 0 }}>
        УпрУчет
      </Typography.Title>

      {organizationsQuery.isError || counterpartiesQuery.isError || currenciesQuery.isError || expenseItemsQuery.isError ? (
        <Alert
          type="error"
          showIcon
          message="Ошибка загрузки справочников"
          description={
            apiError(organizationsQuery.error, "") ||
            apiError(counterpartiesQuery.error, "") ||
            apiError(currenciesQuery.error, "") ||
            apiError(expenseItemsQuery.error, "")
          }
        />
      ) : null}

      <Tabs
        items={[
          {
            key: "organizations",
            label: "Организации",
            children: <DictionaryTable title="Организации" data={organizationsQuery.data ?? []} loading={organizationsQuery.isLoading} showSource />,
          },
          {
            key: "counterparties",
            label: "Контрагенты",
            children: <DictionaryTable title="Контрагенты" data={counterpartiesQuery.data ?? []} loading={counterpartiesQuery.isLoading} showSource />,
          },
          {
            key: "contracts",
            label: "Договоры",
            children: (
              <Card size="small" title="Договоры контрагентов">
                <Form form={contractFilterForm} layout="inline" style={{ marginBottom: 12 }}>
                  <Form.Item name="organization_id" label="Организация">
                    <Select
                      allowClear
                      style={{ width: 320 }}
                      options={(organizationsQuery.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
                    />
                  </Form.Item>
                  <Form.Item name="counterparty_id" label="Контрагент">
                    <Select
                      allowClear
                      style={{ width: 320 }}
                      options={(counterpartiesQuery.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
                    />
                  </Form.Item>
                </Form>
                <Table<CounterpartyContractItem>
                  rowKey="id"
                  loading={contractsQuery.isLoading}
                  dataSource={contractsQuery.data ?? []}
                  columns={contractColumns}
                />
              </Card>
            ),
          },
          {
            key: "currencies",
            label: "Валюты",
            children: <DictionaryTable title="Валюты" data={currenciesQuery.data ?? []} loading={currenciesQuery.isLoading} showSource />,
          },
          {
            key: "cash-flow-operation-types",
            label: "Виды операций ДС",
            children: (
              <Card
                size="small"
                title="Виды операций денежных средств"
                extra={
                  <Can permission="accounting.manage">
                    <Button
                      type="primary"
                      onClick={() => {
                        setEditingOperation(null);
                        operationForm.resetFields();
                        setOperationModalOpen(true);
                      }}
                    >
                      Создать
                    </Button>
                  </Can>
                }
              >
                <Table
                  rowKey="id"
                  loading={operationsQuery.isLoading}
                  dataSource={operationsData}
                  columns={[
                    { title: "Code", dataIndex: "code" },
                    { title: "Name", dataIndex: "name" },
                    { title: "Active", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Yes" : "No"}</Tag> },
                    {
                      title: "Actions",
                      render: (_, row: AccountingDictionaryItem) => (
                        <Can permission="accounting.manage">
                          <Space>
                            <Button
                              onClick={() => {
                                setEditingOperation(row);
                                operationForm.setFieldsValue({ code: row.code, name: row.name, description: null, sort_order: 100 });
                                setOperationModalOpen(true);
                              }}
                            >
                              Edit
                            </Button>
                            <Button danger onClick={() => deactivateOperationMutation.mutate(row.id)}>
                              Deactivate
                            </Button>
                          </Space>
                        </Can>
                      ),
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: "projects",
            label: "Проекты",
            children: (
              <Card
                size="small"
                title="Проекты"
                extra={
                  <Can permission="accounting.manage">
                    <Button
                      type="primary"
                      onClick={() => {
                        setEditingProject(null);
                        projectForm.resetFields();
                        setProjectModalOpen(true);
                      }}
                    >
                      Создать
                    </Button>
                  </Can>
                }
              >
                <Table
                  rowKey="id"
                  loading={projectsQuery.isLoading}
                  dataSource={projectsData}
                  columns={[
                    { title: "Code", dataIndex: "code" },
                    { title: "Name", dataIndex: "name" },
                    { title: "Active", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Yes" : "No"}</Tag> },
                    {
                      title: "Actions",
                      render: (_, row: AccountingDictionaryItem) => (
                        <Can permission="accounting.manage">
                          <Space>
                            <Button
                              onClick={() => {
                                setEditingProject(row);
                                projectForm.setFieldsValue({ code: row.code, name: row.name, description: null });
                                setProjectModalOpen(true);
                              }}
                            >
                              Edit
                            </Button>
                            <Button danger onClick={() => deactivateProjectMutation.mutate(row.id)}>
                              Deactivate
                            </Button>
                          </Space>
                        </Can>
                      ),
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: "expense-items",
            label: "Статьи затрат",
            children: <DictionaryTable title="Статьи затрат" data={expenseItemsQuery.data ?? []} loading={expenseItemsQuery.isLoading} showSource />,
          },
        ]}
      />

      <Modal title={editingOperation ? "Редактировать вид операции" : "Создать вид операции"} open={operationModalOpen} onCancel={() => setOperationModalOpen(false)} footer={null}>
        <Form
          form={operationForm}
          layout="vertical"
          onFinish={(values) => {
            if (editingOperation) {
              updateOperationMutation.mutate({ id: editingOperation.id, payload: values });
            } else {
              createOperationMutation.mutate(values);
            }
          }}
        >
          <Form.Item name="code" label="Code" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Description"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="sort_order" label="Sort order" initialValue={100}><InputNumber style={{ width: "100%" }} /></Form.Item>
          <Button type="primary" htmlType="submit" loading={createOperationMutation.isPending || updateOperationMutation.isPending}>Сохранить</Button>
        </Form>
      </Modal>

      <Modal title={editingProject ? "Редактировать проект" : "Создать проект"} open={projectModalOpen} onCancel={() => setProjectModalOpen(false)} footer={null}>
        <Form
          form={projectForm}
          layout="vertical"
          onFinish={(values) => {
            if (editingProject) {
              updateProjectMutation.mutate({ id: editingProject.id, payload: values });
            } else {
              createProjectMutation.mutate(values);
            }
          }}
        >
          <Form.Item name="code" label="Code" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Description"><Input.TextArea rows={3} /></Form.Item>
          <Button type="primary" htmlType="submit" loading={createProjectMutation.isPending || updateProjectMutation.isPending}>Сохранить</Button>
        </Form>
      </Modal>
    </Space>
  );
};
