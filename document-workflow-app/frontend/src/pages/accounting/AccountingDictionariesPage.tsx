import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Typography, message } from "antd";
import { useMemo, useState } from "react";

import {
  createCashFlowItem,
  createCashFlowOperationType,
  createProject,
  deleteCashFlowOperationType,
  deleteProject,
  getCashFlowItems,
  getCashFlowOperationTypes,
  getCounterparties,
  getCounterpartyContracts,
  getCurrencies,
  getExpenseItems,
  getOrganizations,
  getProjects,
  updateCashFlowItem,
  updateCashFlowOperationType,
  updateProject,
} from "../../entities/accounting";
import type { AccountingDictionaryItem, CashFlowItemDictionaryItem, CounterpartyContractItem } from "../../entities/accounting";
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
  const [cashFlowItemModalOpen, setCashFlowItemModalOpen] = useState(false);
  const [editingOperation, setEditingOperation] = useState<AccountingDictionaryItem | null>(null);
  const [editingProject, setEditingProject] = useState<AccountingDictionaryItem | null>(null);
  const [editingCashFlowItem, setEditingCashFlowItem] = useState<CashFlowItemDictionaryItem | null>(null);
  const [operationForm] = Form.useForm();
  const [projectForm] = Form.useForm();
  const [cashFlowItemForm] = Form.useForm();
  const [contractFilterForm] = Form.useForm();

  const organizationsQuery = useQuery({ queryKey: ["accounting", "organizations"], queryFn: () => getOrganizations({ is_active: true, limit: 100 }) });
  const counterpartiesQuery = useQuery({ queryKey: ["accounting", "counterparties"], queryFn: () => getCounterparties({ is_active: true, limit: 100 }) });
  const currenciesQuery = useQuery({ queryKey: ["accounting", "currencies"], queryFn: () => getCurrencies({ is_active: true, limit: 100 }) });
  const expenseItemsQuery = useQuery({ queryKey: ["accounting", "expense-items"], queryFn: () => getExpenseItems({ is_active: true, limit: 100 }) });
  const cashFlowItemsQuery = useQuery({ queryKey: ["accounting", "cash-flow-items"], queryFn: () => getCashFlowItems({ limit: 100 }) });
  const operationsQuery = useQuery({ queryKey: ["accounting", "cash-flow-operation-types"], queryFn: () => getCashFlowOperationTypes({ limit: 100 }) });
  const projectsQuery = useQuery({ queryKey: ["accounting", "projects"], queryFn: () => getProjects({ limit: 100 }) });

  const organizationId = Form.useWatch("organization_id", contractFilterForm);
  const counterpartyId = Form.useWatch("counterparty_id", contractFilterForm);
  const contractsQuery = useQuery({
    queryKey: ["accounting", "contracts", organizationId, counterpartyId],
    queryFn: () => getCounterpartyContracts({ organization_id: organizationId, counterparty_id: counterpartyId, is_active: true, limit: 100 }),
    enabled: Boolean(organizationId || counterpartyId),
  });

  const createOperationMutation = useMutation({
    mutationFn: createCashFlowOperationType,
    onSuccess: () => {
      message.success("Вид операции создан");
      setOperationModalOpen(false);
      setEditingOperation(null);
      operationForm.resetFields();
      void operationsQuery.refetch();
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
      void operationsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления вида операции")),
  });

  const deactivateOperationMutation = useMutation({
    mutationFn: deleteCashFlowOperationType,
    onSuccess: () => {
      message.success("Вид операции деактивирован");
      void operationsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка деактивации вида операции")),
  });

  const createProjectMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      message.success("Проект создан");
      setProjectModalOpen(false);
      setEditingProject(null);
      projectForm.resetFields();
      void projectsQuery.refetch();
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
      void projectsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления проекта")),
  });

  const deactivateProjectMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      message.success("Проект деактивирован");
      void projectsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка деактивации проекта")),
  });

  const createCashFlowItemMutation = useMutation({
    mutationFn: createCashFlowItem,
    onSuccess: () => {
      message.success("Статья ДДС создана");
      setCashFlowItemModalOpen(false);
      setEditingCashFlowItem(null);
      cashFlowItemForm.resetFields();
      void cashFlowItemsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка создания статьи ДДС")),
  });

  const updateCashFlowItemMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updateCashFlowItem(id, payload),
    onSuccess: () => {
      message.success("Статья ДДС обновлена");
      setCashFlowItemModalOpen(false);
      setEditingCashFlowItem(null);
      cashFlowItemForm.resetFields();
      void cashFlowItemsQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления статьи ДДС")),
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
          { key: "organizations", label: "Организации", children: <DictionaryTable title="Организации" data={organizationsQuery.data ?? []} loading={organizationsQuery.isLoading} showSource /> },
          { key: "counterparties", label: "Контрагенты", children: <DictionaryTable title="Контрагенты" data={counterpartiesQuery.data ?? []} loading={counterpartiesQuery.isLoading} showSource /> },
          {
            key: "contracts",
            label: "Договоры",
            children: (
              <Card size="small" title="Договоры контрагентов">
                <Form form={contractFilterForm} layout="inline" style={{ marginBottom: 12 }}>
                  <Form.Item name="organization_id" label="Организация">
                    <Select allowClear style={{ width: 320 }} options={(organizationsQuery.data ?? []).map((item) => ({ value: item.id, label: item.name }))} />
                  </Form.Item>
                  <Form.Item name="counterparty_id" label="Контрагент">
                    <Select allowClear style={{ width: 320 }} options={(counterpartiesQuery.data ?? []).map((item) => ({ value: item.id, label: item.name }))} />
                  </Form.Item>
                </Form>
                <Table<CounterpartyContractItem> rowKey="id" loading={contractsQuery.isLoading} dataSource={contractsQuery.data ?? []} columns={contractColumns} />
              </Card>
            ),
          },
          { key: "currencies", label: "Валюты", children: <DictionaryTable title="Валюты" data={currenciesQuery.data ?? []} loading={currenciesQuery.isLoading} showSource /> },
          { key: "expense-items", label: "Статьи затрат", children: <DictionaryTable title="Статьи затрат" data={expenseItemsQuery.data ?? []} loading={expenseItemsQuery.isLoading} showSource /> },
          {
            key: "cash-flow-items",
            label: "Статьи ДДС",
            children: (
              <Card
                size="small"
                title="Статьи движения денежных средств"
                extra={
                  <Can permission="accounting.cash_flow_item.manage">
                    <Button
                      type="primary"
                      onClick={() => {
                        setEditingCashFlowItem(null);
                        cashFlowItemForm.resetFields();
                        cashFlowItemForm.setFieldsValue({ direction: "Both", is_active: true, source_system: "1C" });
                        setCashFlowItemModalOpen(true);
                      }}
                    >
                      Создать
                    </Button>
                  </Can>
                }
              >
                <Table
                  rowKey="id"
                  loading={cashFlowItemsQuery.isLoading}
                  dataSource={cashFlowItemsQuery.data ?? []}
                  columns={[
                    { title: "Код", dataIndex: "code" },
                    { title: "Наименование", dataIndex: "name" },
                    { title: "Полное наименование", dataIndex: "full_name" },
                    { title: "Направление", dataIndex: "direction" },
                    { title: "Активен", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Да" : "Нет"}</Tag> },
                    { title: "Источник", dataIndex: "source_system" },
                    { title: "External ID", dataIndex: "external_id" },
                    {
                      title: "Действия",
                      render: (_, row: CashFlowItemDictionaryItem) => (
                        <Can permission="accounting.cash_flow_item.manage">
                          <Button
                            onClick={() => {
                              setEditingCashFlowItem(row);
                              cashFlowItemForm.setFieldsValue(row);
                              setCashFlowItemModalOpen(true);
                            }}
                          >
                            Редактировать
                          </Button>
                        </Can>
                      ),
                    },
                  ]}
                />
              </Card>
            ),
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
                  dataSource={operationsQuery.data ?? []}
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
                  dataSource={projectsQuery.data ?? []}
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
        ]}
      />

      <Modal title={editingCashFlowItem ? "Редактировать статью ДДС" : "Создать статью ДДС"} open={cashFlowItemModalOpen} onCancel={() => setCashFlowItemModalOpen(false)} footer={null}>
        <Form
          form={cashFlowItemForm}
          layout="vertical"
          onFinish={(values) => {
            if (editingCashFlowItem) {
              updateCashFlowItemMutation.mutate({ id: editingCashFlowItem.id, payload: values });
            } else {
              createCashFlowItemMutation.mutate(values);
            }
          }}
        >
          <Form.Item name="external_id" label="External ID"><Input /></Form.Item>
          <Form.Item name="code" label="Код"><Input /></Form.Item>
          <Form.Item name="name" label="Наименование" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="full_name" label="Полное наименование"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="direction" label="Направление" rules={[{ required: true }]}>
            <Select options={[{ value: "Inflow", label: "Inflow" }, { value: "Outflow", label: "Outflow" }, { value: "Both", label: "Both" }]} />
          </Form.Item>
          <Form.Item name="source_system" label="Источник"><Input /></Form.Item>
          <Form.Item name="is_active" label="Статус">
            <Select options={[{ value: true, label: "Активен" }, { value: false, label: "Неактивен" }]} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={createCashFlowItemMutation.isPending || updateCashFlowItemMutation.isPending}>Сохранить</Button>
        </Form>
      </Modal>

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
