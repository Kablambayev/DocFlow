import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, DatePicker, Form, Row, Select, Space, Statistic, Table, Tabs, Tag, Typography } from "antd";
import type { Dayjs } from "dayjs";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  getCashFlowItems,
  getCashFlowOperationTypes,
  getCurrencies,
  getOrganizations,
  getProjects,
} from "../../entities/accounting";
import type { AccountingDictionaryItem, CashFlowItemDictionaryItem } from "../../entities/accounting";
import {
  getBddsByItems,
  getBddsByOrganizations,
  getBddsByPeriods,
  getBddsByProjects,
  getBddsDiagnostics,
  getBddsSummary,
} from "../../entities/bdds-report";
import type {
  BddsByItemRow,
  BddsByOrganizationRow,
  BddsByPeriodRow,
  BddsByProjectRow,
  BddsCommonFilters,
  BddsDiagnosticRow,
  BddsDiagnosticType,
  BddsGroupPeriod,
  BddsTotalByCurrency,
} from "../../entities/bdds-report";

const { RangePicker } = DatePicker;

const numberFormatter = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const directionLabels: Record<string, string> = {
  Inflow: "Приход",
  Outflow: "Расход",
  Both: "Оба",
};

const diagnosticLabels: Record<BddsDiagnosticType, string> = {
  needs_enrichment: "Требует дозаполнения",
  ignored: "Игнорируется",
  missing_direction: "Нет направления",
  missing_date: "Нет даты",
  missing_amount: "Нет суммы",
  missing_cash_flow_item: "Нет статьи ДДС",
  missing_currency: "Нет валюты",
  source_changed: "Изменен источник 1С",
};

const allocationStatusLabels: Record<string, string> = {
  NeedsEnrichment: "Требует дозаполнения",
  Completed: "Завершена",
  Ignored: "Игнорируется",
  Draft: "Черновик",
};

const groupPeriodOptions: { value: BddsGroupPeriod; label: string }[] = [
  { value: "day", label: "День" },
  { value: "week", label: "Неделя" },
  { value: "month", label: "Месяц" },
  { value: "quarter", label: "Квартал" },
  { value: "year", label: "Год" },
];

type FilterFormValues = {
  date_range: [Dayjs, Dayjs];
  organization_id?: string;
  project_id?: string;
  cash_flow_item_id?: string;
  cash_flow_operation_type_id?: string;
  currency_id?: string;
  group_period?: BddsGroupPeriod;
};

const toNumber = (value?: number | string | null) => {
  if (value === null || value === undefined || value === "") return 0;
  const next = Number(value);
  return Number.isFinite(next) ? next : 0;
};

const formatMoney = (value?: number | string | null) => numberFormatter.format(toNumber(value));

const formatDate = (value?: string | null) => (value ? dayjs(value).format("DD.MM.YYYY") : "-");

const renderNet = (value?: number | string | null) => {
  const normalized = toNumber(value);
  if (normalized < 0) {
    return <Typography.Text type="danger">{formatMoney(normalized)}</Typography.Text>;
  }
  return <span>{formatMoney(normalized)}</span>;
};

const defaultFilters = (): BddsCommonFilters => ({
  date_from: dayjs().startOf("month").format("YYYY-MM-DD"),
  date_to: dayjs().format("YYYY-MM-DD"),
  group_period: "month",
});

export const BddsReportPage = () => {
  const [filtersForm] = Form.useForm<FilterFormValues>();
  const navigate = useNavigate();
  const [filters, setFilters] = useState<BddsCommonFilters>(defaultFilters);
  const [diagnosticType, setDiagnosticType] = useState<BddsDiagnosticType | undefined>();
  const [diagnosticsPage, setDiagnosticsPage] = useState({ limit: 50, offset: 0 });

  const organizationsQuery = useQuery({ queryKey: ["accounting", "organizations", "bdds-report"], queryFn: () => getOrganizations({ is_active: true, limit: 200 }) });
  const projectsQuery = useQuery({ queryKey: ["accounting", "projects", "bdds-report"], queryFn: () => getProjects({ is_active: true, limit: 200 }) });
  const cashFlowItemsQuery = useQuery({ queryKey: ["accounting", "cash-flow-items", "bdds-report"], queryFn: () => getCashFlowItems({ limit: 200 }) });
  const operationTypesQuery = useQuery({ queryKey: ["accounting", "cash-flow-operation-types", "bdds-report"], queryFn: () => getCashFlowOperationTypes({ limit: 200 }) });
  const currenciesQuery = useQuery({ queryKey: ["accounting", "currencies", "bdds-report"], queryFn: () => getCurrencies({ is_active: true, limit: 200 }) });

  const summaryQuery = useQuery({ queryKey: ["bdds-report", "summary", filters], queryFn: () => getBddsSummary(filters) });
  const byItemsQuery = useQuery({ queryKey: ["bdds-report", "by-items", filters], queryFn: () => getBddsByItems(filters) });
  const byProjectsQuery = useQuery({ queryKey: ["bdds-report", "by-projects", filters], queryFn: () => getBddsByProjects(filters) });
  const byOrganizationsQuery = useQuery({ queryKey: ["bdds-report", "by-organizations", filters], queryFn: () => getBddsByOrganizations(filters) });
  const byPeriodsQuery = useQuery({ queryKey: ["bdds-report", "by-periods", filters], queryFn: () => getBddsByPeriods(filters) });
  const diagnosticsQuery = useQuery({
    queryKey: ["bdds-report", "diagnostics", filters, diagnosticType, diagnosticsPage],
    queryFn: () =>
      getBddsDiagnostics({
        ...filters,
        diagnostic_type: diagnosticType,
        limit: diagnosticsPage.limit,
        offset: diagnosticsPage.offset,
      }),
  });

  const commonError = summaryQuery.error || byItemsQuery.error || byProjectsQuery.error || byOrganizationsQuery.error || byPeriodsQuery.error || diagnosticsQuery.error;

  const dictionaryOptions = (items?: AccountingDictionaryItem[] | CashFlowItemDictionaryItem[]) =>
    (items ?? []).map((item) => ({
      value: item.id,
      label: item.code ? `${item.code} — ${item.name}` : item.name,
    }));

  const applyFilters = (values: FilterFormValues) => {
    setDiagnosticsPage({ limit: 50, offset: 0 });
    setFilters({
      date_from: values.date_range[0].format("YYYY-MM-DD"),
      date_to: values.date_range[1].format("YYYY-MM-DD"),
      organization_id: values.organization_id || undefined,
      project_id: values.project_id || undefined,
      cash_flow_item_id: values.cash_flow_item_id || undefined,
      cash_flow_operation_type_id: values.cash_flow_operation_type_id || undefined,
      currency_id: values.currency_id || undefined,
      group_period: values.group_period || "month",
    });
  };

  const resetFilters = () => {
    const next = defaultFilters();
    filtersForm.setFieldsValue({
      date_range: [dayjs(next.date_from), dayjs(next.date_to)],
      group_period: next.group_period,
      organization_id: undefined,
      project_id: undefined,
      cash_flow_item_id: undefined,
      cash_flow_operation_type_id: undefined,
      currency_id: undefined,
    });
    setDiagnosticType(undefined);
    setDiagnosticsPage({ limit: 50, offset: 0 });
    setFilters(next);
  };

  const summaryCurrencyRows = useMemo<BddsTotalByCurrency[]>(() => {
    const rows = summaryQuery.data?.totals_by_currency ?? [];
    if (rows.length > 0) return rows;
    if (filters.currency_id && summaryQuery.data?.currency) {
      return [
        {
          currency: summaryQuery.data.currency,
          inflow_total: toNumber(summaryQuery.data.inflow_total),
          outflow_total: toNumber(summaryQuery.data.outflow_total),
          net_cash_flow: toNumber(summaryQuery.data.net_cash_flow),
        },
      ];
    }
    return [];
  }, [filters.currency_id, summaryQuery.data]);

  const totalsHaveSingleCurrency = Boolean(filters.currency_id);

  const totalsByCurrencyColumns = [
    { title: "Валюта", render: (_: unknown, row: BddsTotalByCurrency) => row.currency?.code ?? "—" },
    { title: "Приход", render: (_: unknown, row: BddsTotalByCurrency) => formatMoney(row.inflow_total) },
    { title: "Расход", render: (_: unknown, row: BddsTotalByCurrency) => formatMoney(row.outflow_total) },
    { title: "Чистый поток", render: (_: unknown, row: BddsTotalByCurrency) => renderNet(row.net_cash_flow) },
  ];

  const byItemsColumns = [
    { title: "Статья ДДС", render: (_: unknown, row: BddsByItemRow) => row.cash_flow_item?.name ?? "-" },
    { title: "Код", render: (_: unknown, row: BddsByItemRow) => row.cash_flow_item?.code ?? "-" },
    { title: "Направление", render: (_: unknown, row: BddsByItemRow) => directionLabels[row.cash_flow_item?.direction ?? ""] ?? row.cash_flow_item?.direction ?? "-" },
    { title: "Валюта", render: (_: unknown, row: BddsByItemRow) => row.currency?.code ?? "-" },
    { title: "Приход", render: (_: unknown, row: BddsByItemRow) => formatMoney(row.inflow_total) },
    { title: "Расход", render: (_: unknown, row: BddsByItemRow) => formatMoney(row.outflow_total) },
    { title: "Чистый поток", render: (_: unknown, row: BddsByItemRow) => renderNet(row.net_cash_flow) },
    { title: "Количество разноcок", dataIndex: "allocations_count" },
  ];

  const byProjectsColumns = [
    { title: "Проект", render: (_: unknown, row: BddsByProjectRow) => row.project?.name ?? row.project_name ?? "Без проекта" },
    { title: "Код", render: (_: unknown, row: BddsByProjectRow) => row.project?.code ?? "-" },
    { title: "Валюта", render: (_: unknown, row: BddsByProjectRow) => row.currency?.code ?? "-" },
    { title: "Приход", render: (_: unknown, row: BddsByProjectRow) => formatMoney(row.inflow_total) },
    { title: "Расход", render: (_: unknown, row: BddsByProjectRow) => formatMoney(row.outflow_total) },
    { title: "Чистый поток", render: (_: unknown, row: BddsByProjectRow) => renderNet(row.net_cash_flow) },
    { title: "Количество разноcок", dataIndex: "allocations_count" },
  ];

  const byOrganizationsColumns = [
    { title: "Организация", render: (_: unknown, row: BddsByOrganizationRow) => row.organization?.name ?? "-" },
    { title: "Валюта", render: (_: unknown, row: BddsByOrganizationRow) => row.currency?.code ?? "-" },
    { title: "Приход", render: (_: unknown, row: BddsByOrganizationRow) => formatMoney(row.inflow_total) },
    { title: "Расход", render: (_: unknown, row: BddsByOrganizationRow) => formatMoney(row.outflow_total) },
    { title: "Чистый поток", render: (_: unknown, row: BddsByOrganizationRow) => renderNet(row.net_cash_flow) },
    { title: "Количество разноcок", dataIndex: "allocations_count" },
  ];

  const byPeriodsColumns = [
    { title: "Период", render: (_: unknown, row: BddsByPeriodRow) => `${formatDate(row.period_start)} — ${formatDate(row.period_end)}` },
    { title: "Валюта", render: (_: unknown, row: BddsByPeriodRow) => row.currency?.code ?? "-" },
    { title: "Приход", render: (_: unknown, row: BddsByPeriodRow) => formatMoney(row.inflow_total) },
    { title: "Расход", render: (_: unknown, row: BddsByPeriodRow) => formatMoney(row.outflow_total) },
    { title: "Чистый поток", render: (_: unknown, row: BddsByPeriodRow) => renderNet(row.net_cash_flow) },
    { title: "Количество разноcок", dataIndex: "allocations_count" },
  ];

  const diagnosticsColumns = [
    {
      title: "Тип",
      render: (_: unknown, row: BddsDiagnosticRow) => <Tag>{diagnosticLabels[row.diagnostic_type] ?? row.diagnostic_type}</Tag>,
    },
    { title: "Дата", render: (_: unknown, row: BddsDiagnosticRow) => formatDate(row.source_document_date) },
    { title: "Документ 1С", dataIndex: "source_document_type_1c", width: 220 },
    { title: "Номер", dataIndex: "source_document_number", width: 160 },
    { title: "Статус разноски", render: (_: unknown, row: BddsDiagnosticRow) => allocationStatusLabels[row.allocation_status ?? ""] ?? row.allocation_status ?? "-" },
    { title: "Сообщение", dataIndex: "message", width: 360 },
    {
      title: "Действия",
      render: () => (
        <Button size="small" onClick={() => navigate(`/cash-flow/allocations`)}>
          Открыть разноску
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Отчет БДДС
        </Typography.Title>
        <Typography.Text type="secondary">
          Движение денежных средств по завершенным разноскам БДДС
        </Typography.Text>
      </div>

      {commonError ? (
        <Alert type="error" showIcon message={apiError(commonError, "Не удалось загрузить отчет БДДС")} />
      ) : null}

      <Card>
        <Form
          form={filtersForm}
          layout="vertical"
          initialValues={{
            date_range: [dayjs(filters.date_from), dayjs(filters.date_to)],
            group_period: filters.group_period,
          }}
          onFinish={applyFilters}
        >
          <Row gutter={[16, 8]}>
            <Col xs={24} md={12} lg={6}>
              <Form.Item name="date_range" label="Период" rules={[{ required: true, message: "Период обязателен" }]}>
                <RangePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item name="organization_id" label="Организация">
                <Select allowClear showSearch optionFilterProp="label" options={dictionaryOptions(organizationsQuery.data)} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item name="project_id" label="Проект">
                <Select allowClear showSearch optionFilterProp="label" options={dictionaryOptions(projectsQuery.data)} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item name="cash_flow_item_id" label="Статья ДДС">
                <Select allowClear showSearch optionFilterProp="label" options={dictionaryOptions(cashFlowItemsQuery.data)} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item name="cash_flow_operation_type_id" label="Вид операции ДС">
                <Select allowClear showSearch optionFilterProp="label" options={dictionaryOptions(operationTypesQuery.data)} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item name="currency_id" label="Валюта">
                <Select allowClear showSearch optionFilterProp="label" options={dictionaryOptions(currenciesQuery.data)} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item name="group_period" label="Период группировки">
                <Select options={groupPeriodOptions} />
              </Form.Item>
            </Col>
          </Row>
          <Space>
            <Button type="primary" htmlType="submit">
              Сформировать
            </Button>
            <Button onClick={resetFilters}>Сбросить</Button>
          </Space>
        </Form>
      </Card>

      {!totalsHaveSingleCurrency ? (
        <Alert
          type="info"
          showIcon
          message="Выбрано несколько валют"
          description="Общие денежные итоги не смешиваются между валютами. Используйте сводку по валютам ниже или выберите конкретную валюту в фильтрах."
        />
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={summaryQuery.isLoading}>
            <Statistic
              title="Приход"
              value={totalsHaveSingleCurrency ? toNumber(summaryQuery.data?.inflow_total) : undefined}
              formatter={(value) => (value === undefined ? "Несколько валют" : formatMoney(value as number))}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={summaryQuery.isLoading}>
            <Statistic
              title="Расход"
              value={totalsHaveSingleCurrency ? toNumber(summaryQuery.data?.outflow_total) : undefined}
              formatter={(value) => (value === undefined ? "Несколько валют" : formatMoney(value as number))}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={summaryQuery.isLoading}>
            <Statistic
              title="Чистый поток"
              value={totalsHaveSingleCurrency ? toNumber(summaryQuery.data?.net_cash_flow) : undefined}
              formatter={(value) => {
                if (value === undefined) return "Несколько валют";
                return formatMoney(value as number);
              }}
              valueStyle={totalsHaveSingleCurrency && toNumber(summaryQuery.data?.net_cash_flow) < 0 ? { color: "#cf1322" } : undefined}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={summaryQuery.isLoading}>
            <Statistic title="Разносок в отчете" value={summaryQuery.data?.allocations_count ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={summaryQuery.isLoading}>
            <Statistic title="Требуют дозаполнения" value={summaryQuery.data?.diagnostics.needs_enrichment_count ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={summaryQuery.isLoading}>
            <Statistic title="Игнорируются" value={summaryQuery.data?.diagnostics.ignored_allocations_count ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={summaryQuery.isLoading}>
            <Statistic title="Проблемные Completed" value={summaryQuery.data?.diagnostics.invalid_allocations_count ?? 0} />
          </Card>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: "currencies",
            label: "Сводка по валютам",
            children: (
              <Table<BddsTotalByCurrency>
                rowKey={(row) => row.currency?.id ?? "no-currency"}
                loading={summaryQuery.isLoading}
                dataSource={summaryCurrencyRows}
                columns={totalsByCurrencyColumns}
                pagination={false}
              />
            ),
          },
          {
            key: "items",
            label: "По статьям ДДС",
            children: (
              <Table<BddsByItemRow>
                rowKey={(row) => `${row.cash_flow_item?.id ?? "no-item"}-${row.currency?.id ?? "no-currency"}`}
                loading={byItemsQuery.isLoading}
                dataSource={byItemsQuery.data?.items ?? []}
                columns={byItemsColumns}
                pagination={false}
                scroll={{ x: 1200 }}
              />
            ),
          },
          {
            key: "projects",
            label: "По проектам",
            children: (
              <Table<BddsByProjectRow>
                rowKey={(row) => `${row.project?.id ?? "no-project"}-${row.currency?.id ?? "no-currency"}`}
                loading={byProjectsQuery.isLoading}
                dataSource={byProjectsQuery.data?.items ?? []}
                columns={byProjectsColumns}
                pagination={false}
                scroll={{ x: 1100 }}
              />
            ),
          },
          {
            key: "organizations",
            label: "По организациям",
            children: (
              <Table<BddsByOrganizationRow>
                rowKey={(row) => `${row.organization?.id ?? "no-organization"}-${row.currency?.id ?? "no-currency"}`}
                loading={byOrganizationsQuery.isLoading}
                dataSource={byOrganizationsQuery.data?.items ?? []}
                columns={byOrganizationsColumns}
                pagination={false}
                scroll={{ x: 1000 }}
              />
            ),
          },
          {
            key: "periods",
            label: "По периодам",
            children: (
              <Table<BddsByPeriodRow>
                rowKey={(row) => `${row.period_start}-${row.period_end}-${row.currency?.id ?? "no-currency"}`}
                loading={byPeriodsQuery.isLoading}
                dataSource={byPeriodsQuery.data?.items ?? []}
                columns={byPeriodsColumns}
                pagination={false}
                scroll={{ x: 1000 }}
              />
            ),
          },
          {
            key: "diagnostics",
            label: "Диагностика",
            children: (
              <Space direction="vertical" size={16} style={{ width: "100%" }}>
                <Card size="small">
                  <Space wrap>
                    <Typography.Text>Тип диагностики</Typography.Text>
                    <Select<BddsDiagnosticType>
                      allowClear
                      placeholder="Все типы"
                      style={{ width: 280 }}
                      value={diagnosticType}
                      onChange={(value) => {
                        setDiagnosticType(value);
                        setDiagnosticsPage((prev) => ({ ...prev, offset: 0 }));
                      }}
                      options={Object.entries(diagnosticLabels).map(([value, label]) => ({ value: value as BddsDiagnosticType, label }))}
                    />
                  </Space>
                </Card>
                <Table<BddsDiagnosticRow>
                  rowKey={(row) => `${row.document_id}-${row.diagnostic_type}`}
                  loading={diagnosticsQuery.isLoading}
                  dataSource={diagnosticsQuery.data?.items ?? []}
                  columns={diagnosticsColumns}
                  scroll={{ x: 1200 }}
                  pagination={{
                    total: diagnosticsQuery.data?.total ?? 0,
                    pageSize: diagnosticsQuery.data?.limit ?? diagnosticsPage.limit,
                    current: Math.floor((diagnosticsQuery.data?.offset ?? diagnosticsPage.offset) / (diagnosticsQuery.data?.limit ?? diagnosticsPage.limit)) + 1,
                    onChange: (page, pageSize) => setDiagnosticsPage({ limit: pageSize, offset: (page - 1) * pageSize }),
                  }}
                />
              </Space>
            ),
          },
        ]}
      />
    </Space>
  );
};
