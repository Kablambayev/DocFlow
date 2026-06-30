import { EditOutlined, EyeOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, DatePicker, Descriptions, Drawer, Form, Input, Row, Select, Space, Statistic, Table, Tag, Typography, message } from "antd";
import type { Dayjs } from "dayjs";
import dayjs from "dayjs";
import { useEffect, useState } from "react";

import {
  getCashFlowItems,
  getCashFlowOperationTypes,
  getCounterparties,
  getCurrencies,
  getOrganizations,
  getProjects,
} from "../../entities/accounting";
import type { AccountingDictionaryItem, CashFlowItemDictionaryItem } from "../../entities/accounting";
import {
  completeCashFlowAllocation,
  getCashFlowAllocation,
  getCashFlowAllocationMetrics,
  getCashFlowAllocations,
  ignoreCashFlowAllocation,
  reopenCashFlowAllocation,
  updateCashFlowAllocation,
} from "../../entities/cash-flow-allocation";
import type {
  CashFlowAllocationDetail,
  CashFlowAllocationListItem,
  CashFlowAllocationQueryParams,
  CashFlowAllocationStatus,
} from "../../entities/cash-flow-allocation";
import { Can } from "../../shared/auth/Can";

const { RangePicker } = DatePicker;

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const statusMeta: Record<string, { label: string; color: string }> = {
  NeedsEnrichment: { label: "Требует дозаполнения", color: "orange" },
  Completed: { label: "Завершена", color: "green" },
  Ignored: { label: "Игнорируется", color: "default" },
  Draft: { label: "Черновик", color: "blue" },
};

const directionMeta: Record<string, { label: string; color: string }> = {
  Inflow: { label: "Приход", color: "green" },
  Outflow: { label: "Расход", color: "red" },
};

type FilterValues = {
  allocation_status?: CashFlowAllocationStatus;
  cash_flow_direction?: "Inflow" | "Outflow";
  organization_id?: string;
  counterparty_id?: string;
  project_id?: string;
  cash_flow_item_id?: string;
  currency_id?: string;
  source_changed?: "true" | "false";
  date_range?: [Dayjs, Dayjs];
  search?: string;
};

type EditFormValues = {
  cash_flow_item_id?: string;
  project_id?: string;
  cash_flow_operation_type_id?: string;
  management_comment?: string;
  allocation_status?: CashFlowAllocationStatus;
};

const formatAmount = (value?: number | null) => new Intl.NumberFormat("ru-RU").format(value ?? 0);

export const CashFlowAllocationsPage = () => {
  const [filtersForm] = Form.useForm<FilterValues>();
  const [editForm] = Form.useForm<EditFormValues>();
  const [filters, setFilters] = useState<CashFlowAllocationQueryParams>({ limit: 50, offset: 0 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const organizationsQuery = useQuery({ queryKey: ["accounting", "organizations", "cash-flow-allocations"], queryFn: () => getOrganizations({ is_active: true, limit: 200 }) });
  const counterpartiesQuery = useQuery({ queryKey: ["accounting", "counterparties", "cash-flow-allocations"], queryFn: () => getCounterparties({ is_active: true, limit: 200 }) });
  const projectsQuery = useQuery({ queryKey: ["accounting", "projects", "cash-flow-allocations"], queryFn: () => getProjects({ is_active: true, limit: 200 }) });
  const currenciesQuery = useQuery({ queryKey: ["accounting", "currencies", "cash-flow-allocations"], queryFn: () => getCurrencies({ is_active: true, limit: 200 }) });
  const cashFlowItemsQuery = useQuery({ queryKey: ["accounting", "cash-flow-items", "cash-flow-allocations"], queryFn: () => getCashFlowItems({ limit: 200 }) });
  const operationTypesQuery = useQuery({ queryKey: ["accounting", "cash-flow-operation-types", "cash-flow-allocations"], queryFn: () => getCashFlowOperationTypes({ limit: 200 }) });

  const allocationsQuery = useQuery({ queryKey: ["cash-flow-allocations", filters], queryFn: () => getCashFlowAllocations(filters) });
  const metricsQuery = useQuery({ queryKey: ["cash-flow-allocations-metrics"], queryFn: getCashFlowAllocationMetrics });
  const detailQuery = useQuery({
    queryKey: ["cash-flow-allocation", selectedId],
    queryFn: () => getCashFlowAllocation(selectedId as string),
    enabled: Boolean(selectedId),
  });

  const refreshData = async () => {
    await Promise.all([allocationsQuery.refetch(), metricsQuery.refetch(), detailQuery.refetch()]);
  };

  const updateMutation = useMutation({
    mutationFn: ({ documentId, values }: { documentId: string; values: EditFormValues }) => updateCashFlowAllocation(documentId, values),
    onSuccess: async () => {
      message.success("Разноска обновлена");
      await refreshData();
    },
    onError: (error) => message.error(apiError(error, "Не удалось обновить разноску")),
  });

  const completeMutation = useMutation({
    mutationFn: (documentId: string) => completeCashFlowAllocation(documentId),
    onSuccess: async () => {
      message.success("Разноска завершена");
      await refreshData();
    },
    onError: (error) => message.error(apiError(error, "Не удалось завершить разноску")),
  });

  const ignoreMutation = useMutation({
    mutationFn: (documentId: string) => ignoreCashFlowAllocation(documentId),
    onSuccess: async () => {
      message.success("Разноска переведена в Ignore");
      await refreshData();
    },
    onError: (error) => message.error(apiError(error, "Не удалось игнорировать разноску")),
  });

  const reopenMutation = useMutation({
    mutationFn: (documentId: string) => reopenCashFlowAllocation(documentId),
    onSuccess: async () => {
      message.success("Разноска переоткрыта");
      await refreshData();
    },
    onError: (error) => message.error(apiError(error, "Не удалось переоткрыть разноску")),
  });

  const selectedItem = detailQuery.data;

  const openDrawer = (documentId: string) => {
    setSelectedId(documentId);
    setDrawerOpen(true);
  };

  const applyFilters = (values: FilterValues) => {
    setFilters({
      allocation_status: values.allocation_status,
      cash_flow_direction: values.cash_flow_direction,
      organization_id: values.organization_id,
      counterparty_id: values.counterparty_id,
      project_id: values.project_id,
      cash_flow_item_id: values.cash_flow_item_id,
      currency_id: values.currency_id,
      source_changed: values.source_changed === undefined ? undefined : values.source_changed === "true",
      date_from: values.date_range?.[0]?.format("YYYY-MM-DD"),
      date_to: values.date_range?.[1]?.format("YYYY-MM-DD"),
      search: values.search?.trim() || undefined,
      limit: filters.limit ?? 50,
      offset: 0,
    });
  };

  const resetFilters = () => {
    filtersForm.resetFields();
    setFilters({ limit: 50, offset: 0 });
  };

  const setEditValues = (detail?: CashFlowAllocationDetail) => {
    editForm.setFieldsValue({
      cash_flow_item_id: detail?.cash_flow_item?.id,
      project_id: detail?.project?.id,
      cash_flow_operation_type_id: detail?.cash_flow_operation_type?.id,
      management_comment: detail?.management_comment ?? undefined,
      allocation_status: detail?.allocation_status,
    });
  };

  useEffect(() => {
    if (selectedItem) {
      setEditValues(selectedItem);
    }
  }, [selectedItem]); // eslint-disable-line react-hooks/exhaustive-deps

  const accountingOptions = (items?: AccountingDictionaryItem[] | CashFlowItemDictionaryItem[]) =>
    (items ?? []).map((item) => ({ value: item.id, label: item.code ? `${item.code} — ${item.name}` : item.name }));

  const columns = [
    { title: "Дата", dataIndex: "source_document_date", render: (value?: string | null) => (value ? dayjs(value).format("DD.MM.YYYY") : "-") },
    { title: "Документ 1С", dataIndex: "source_document_type_1c", width: 220 },
    { title: "Номер", dataIndex: "source_document_number", width: 140 },
    {
      title: "Направление",
      dataIndex: "cash_flow_direction",
      render: (value?: string | null) => {
        if (!value) return "-";
        const meta = directionMeta[value] ?? { label: value, color: "default" };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    { title: "Организация", render: (_: unknown, row: CashFlowAllocationListItem) => row.organization?.name ?? "-" },
    { title: "Контрагент", render: (_: unknown, row: CashFlowAllocationListItem) => row.counterparty?.name ?? "-" },
    { title: "Назначение", dataIndex: "payment_purpose", ellipsis: true, width: 240 },
    { title: "Приход", render: (_: unknown, row: CashFlowAllocationListItem) => (row.cash_flow_direction === "Inflow" ? formatAmount(row.amount) : "-") },
    { title: "Расход", render: (_: unknown, row: CashFlowAllocationListItem) => (row.cash_flow_direction === "Outflow" ? formatAmount(row.amount) : "-") },
    { title: "Проект", render: (_: unknown, row: CashFlowAllocationListItem) => row.project?.code ?? row.project?.name ?? "-" },
    { title: "Статья ДДС", render: (_: unknown, row: CashFlowAllocationListItem) => row.cash_flow_item?.name ?? "-" },
    {
      title: "Статус",
      dataIndex: "allocation_status",
      render: (value: string) => {
        const meta = statusMeta[value] ?? { label: value, color: "default" };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    { title: "Источник изменен", render: (_: unknown, row: CashFlowAllocationListItem) => (row.source_changed ? <Tag color="red">Да</Tag> : "-") },
    {
      title: "Действия",
      render: (_: unknown, row: CashFlowAllocationListItem) => (
        <Space wrap>
          <Button size="small" icon={<EyeOutlined />} onClick={() => openDrawer(row.document_id)}>Открыть</Button>
          <Can permission="cash_flow.allocation.manage">
            <Button size="small" icon={<EditOutlined />} onClick={() => openDrawer(row.document_id)}>Дозаполнить</Button>
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div>
        <Typography.Title level={4} style={{ margin: 0 }}>Разноски БДДС</Typography.Title>
        <Typography.Text type="secondary">Денежные документы 1С с аналитикой для отчета БДДС</Typography.Text>
      </div>

      {allocationsQuery.isError || metricsQuery.isError ? (
        <Alert type="error" showIcon message={apiError(allocationsQuery.error ?? metricsQuery.error, "Не удалось загрузить реестр разносок БДДС")} />
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="Требуют дозаполнения" value={metricsQuery.data?.needs_enrichment ?? 0} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="Завершены" value={metricsQuery.data?.completed ?? 0} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="Игнорируются" value={metricsQuery.data?.ignored ?? 0} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="Изменен источник 1С" value={metricsQuery.data?.source_changed ?? 0} /></Card></Col>
      </Row>

      <Card>
        <Form form={filtersForm} layout="vertical" onFinish={applyFilters}>
          <Row gutter={[16, 8]}>
            <Col xs={24} md={8} lg={4}><Form.Item name="date_range" label="Период"><RangePicker style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={8} lg={4}><Form.Item name="allocation_status" label="Статус"><Select allowClear options={Object.entries(statusMeta).map(([value, meta]) => ({ value, label: meta.label }))} /></Form.Item></Col>
            <Col xs={24} md={8} lg={4}><Form.Item name="cash_flow_direction" label="Направление"><Select allowClear options={[{ value: "Inflow", label: "Приход" }, { value: "Outflow", label: "Расход" }]} /></Form.Item></Col>
            <Col xs={24} md={8} lg={6}><Form.Item name="organization_id" label="Организация"><Select allowClear showSearch optionFilterProp="label" options={accountingOptions(organizationsQuery.data)} /></Form.Item></Col>
            <Col xs={24} md={8} lg={6}><Form.Item name="counterparty_id" label="Контрагент"><Select allowClear showSearch optionFilterProp="label" options={accountingOptions(counterpartiesQuery.data)} /></Form.Item></Col>
            <Col xs={24} md={8} lg={6}><Form.Item name="project_id" label="Проект"><Select allowClear showSearch optionFilterProp="label" options={accountingOptions(projectsQuery.data)} /></Form.Item></Col>
            <Col xs={24} md={8} lg={6}><Form.Item name="cash_flow_item_id" label="Статья ДДС"><Select allowClear showSearch optionFilterProp="label" options={accountingOptions(cashFlowItemsQuery.data)} /></Form.Item></Col>
            <Col xs={24} md={8} lg={4}><Form.Item name="currency_id" label="Валюта"><Select allowClear showSearch optionFilterProp="label" options={accountingOptions(currenciesQuery.data)} /></Form.Item></Col>
            <Col xs={24} md={8} lg={4}><Form.Item name="source_changed" label="Источник изменен"><Select allowClear options={[{ value: "true", label: "Да" }, { value: "false", label: "Нет" }]} /></Form.Item></Col>
            <Col xs={24} lg={10}><Form.Item name="search" label="Поиск"><Input placeholder="Номер, документ 1С или назначение платежа" /></Form.Item></Col>
          </Row>
          <Space>
            <Button type="primary" htmlType="submit">Применить</Button>
            <Button onClick={resetFilters}>Сбросить</Button>
          </Space>
        </Form>
      </Card>

      <Card>
        <Table<CashFlowAllocationListItem>
          rowKey="document_id"
          loading={allocationsQuery.isLoading}
          dataSource={allocationsQuery.data?.items ?? []}
          columns={columns}
          scroll={{ x: 1800 }}
          pagination={{
            total: allocationsQuery.data?.total ?? 0,
            pageSize: filters.limit ?? 50,
            current: Math.floor((filters.offset ?? 0) / (filters.limit ?? 50)) + 1,
            onChange: (page, pageSize) => setFilters((prev) => ({ ...prev, offset: (page - 1) * pageSize, limit: pageSize })),
          }}
        />
      </Card>

      <Drawer
        open={drawerOpen}
        width={900}
        title="Разноска БДДС"
        onClose={() => setDrawerOpen(false)}
        destroyOnClose={false}
      >
        {selectedItem?.source_changed ? (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message="Источник 1С изменился после ручной разноски. Проверьте сумму, дату, валюту и аналитику."
          />
        ) : null}

        {detailQuery.isError ? <Alert type="error" showIcon message={apiError(detailQuery.error, "Не удалось загрузить детальную карточку разноски")} /> : null}

        {selectedItem ? (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Card type="inner" title="Источник 1С">
              <Descriptions bordered column={1}>
                <Descriptions.Item label="Тип документа 1С">{selectedItem.source_document_type_1c ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Номер">{selectedItem.source_document_number ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Дата">{selectedItem.source_document_date ? dayjs(selectedItem.source_document_date).format("DD.MM.YYYY") : "-"}</Descriptions.Item>
                <Descriptions.Item label="Сумма">{formatAmount(selectedItem.source_document_amount)}</Descriptions.Item>
                <Descriptions.Item label="Валюта">{selectedItem.source_document_currency?.code ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Организация">{selectedItem.organization?.name ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Контрагент">{selectedItem.counterparty?.name ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Договор">{selectedItem.contract?.name ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Назначение платежа">{selectedItem.source_document_purpose ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Комментарий">{selectedItem.source_document_comment ?? "-"}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Can permission="cash_flow.allocation.manage">
              <Card type="inner" title="Аналитика БДДС">
                <Form form={editForm} layout="vertical">
                  <Form.Item name="cash_flow_item_id" label="Статья ДДС"><Select allowClear showSearch optionFilterProp="label" options={accountingOptions(cashFlowItemsQuery.data)} /></Form.Item>
                  <Form.Item name="project_id" label="Проект"><Select allowClear showSearch optionFilterProp="label" options={accountingOptions(projectsQuery.data)} /></Form.Item>
                  <Form.Item name="cash_flow_operation_type_id" label="Вид операции ДС"><Select allowClear showSearch optionFilterProp="label" options={accountingOptions(operationTypesQuery.data)} /></Form.Item>
                  <Form.Item name="management_comment" label="Комментарий управленческого учета"><Input.TextArea rows={3} /></Form.Item>
                  <Space wrap>
                    <Button type="primary" onClick={() => selectedId && updateMutation.mutate({ documentId: selectedId, values: editForm.getFieldsValue() })} loading={updateMutation.isPending}>Сохранить</Button>
                    <Button onClick={() => selectedId && completeMutation.mutate(selectedId)} loading={completeMutation.isPending}>Завершить разноску</Button>
                    <Button onClick={() => selectedId && ignoreMutation.mutate(selectedId)} loading={ignoreMutation.isPending}>Игнорировать</Button>
                    <Button onClick={() => selectedId && reopenMutation.mutate(selectedId)} loading={reopenMutation.isPending}>Переоткрыть</Button>
                  </Space>
                </Form>
              </Card>
            </Can>

            <Card type="inner" title="Диагностика">
              <Descriptions bordered column={1}>
                <Descriptions.Item label="allocation_status">{selectedItem.allocation_status}</Descriptions.Item>
                <Descriptions.Item label="missing_required_fields">{(selectedItem.missing_required_fields ?? []).join(", ") || "-"}</Descriptions.Item>
                <Descriptions.Item label="source_changed">{selectedItem.source_changed ? "true" : "false"}</Descriptions.Item>
                <Descriptions.Item label="mapping_rule_id">{selectedItem.mapping_rule_id ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="mapping_result">{selectedItem.mapping_result ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="raw_source_payload">
                  <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(selectedItem.raw_source_payload ?? {}, null, 2)}</pre>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Space>
        ) : null}
      </Drawer>
    </Space>
  );
};
