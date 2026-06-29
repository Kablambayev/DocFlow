import { ExclamationCircleOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, InputNumber, Modal, Row, Select, Space, Statistic, Table, Tag, Typography, message } from "antd";
import type { Dayjs } from "dayjs";
import dayjs from "dayjs";
import { useState } from "react";
import { Link } from "react-router-dom";

import { getCounterparties, getOrganizations, getProjects } from "../../entities/accounting";
import type { AccountingDictionaryItem } from "../../entities/accounting";
import { sendPaymentRequestTo1C } from "../../entities/integration1c";
import { getTreasuryPaymentRequestMetrics, getTreasuryPaymentRequests } from "../../entities/treasury";
import type { TreasuryPaymentRequest, TreasuryPaymentRequestQueryParams } from "../../entities/treasury";
import { useAuth } from "../../shared/auth/useAuth";

const { RangePicker } = DatePicker;

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const exportStatusOptions = [
  { value: "not_exported", label: "Не отправлено" },
  { value: "Pending", label: "В очереди" },
  { value: "Sent", label: "Отправлено" },
  { value: "CreatedIn1C", label: "Создано в 1С" },
  { value: "AlreadyExistsIn1C", label: "Уже было в 1С" },
  { value: "Failed", label: "Ошибка" },
];

const exportStatusMeta: Record<string, { label: string; color: string }> = {
  not_exported: { label: "Не отправлено", color: "default" },
  Pending: { label: "В очереди", color: "blue" },
  Sent: { label: "Отправлено", color: "blue" },
  CreatedIn1C: { label: "Создано в 1С", color: "green" },
  AlreadyExistsIn1C: { label: "Уже было в 1С", color: "green" },
  Failed: { label: "Ошибка", color: "red" },
};

type FilterValues = {
  export_status?: string;
  organization_id?: string;
  counterparty_id?: string;
  project_id?: string;
  search?: string;
  amount_from?: number;
  amount_to?: number;
  date_range?: [Dayjs, Dayjs];
};

const metricCurrency = (value: number) => new Intl.NumberFormat("ru-RU").format(value ?? 0);

export const TreasuryPaymentRequestsPage = () => {
  const { hasPermission } = useAuth();
  const [form] = Form.useForm<FilterValues>();
  const [modal, modalContextHolder] = Modal.useModal();
  const [filters, setFilters] = useState<TreasuryPaymentRequestQueryParams>({
    approval_status: "Approved",
    limit: 50,
    offset: 0,
    sort_by: "approved_at",
    sort_order: "desc",
  });
  const [errorRow, setErrorRow] = useState<TreasuryPaymentRequest | null>(null);
  const canSend = hasPermission("integration_1c.payment_request.send");
  const canReadIntegrationLogs = hasPermission("integration.log.read");

  const organizationsQuery = useQuery({ queryKey: ["accounting", "organizations", "treasury-filter"], queryFn: () => getOrganizations({ is_active: true, limit: 200 }) });
  const counterpartiesQuery = useQuery({ queryKey: ["accounting", "counterparties", "treasury-filter"], queryFn: () => getCounterparties({ is_active: true, limit: 200 }) });
  const projectsQuery = useQuery({ queryKey: ["accounting", "projects", "treasury-filter"], queryFn: () => getProjects({ is_active: true, limit: 200 }) });

  const registryQuery = useQuery({
    queryKey: ["treasury", "payment-requests", filters],
    queryFn: () => getTreasuryPaymentRequests(filters),
  });

  const metricsQuery = useQuery({
    queryKey: ["treasury", "payment-requests", "metrics"],
    queryFn: getTreasuryPaymentRequestMetrics,
  });

  const sendMutation = useMutation({
    mutationFn: ({ documentId, force }: { documentId: string; force: boolean }) => sendPaymentRequestTo1C(documentId, force),
    onSuccess: async (result) => {
      if (result.status === "Failed") {
        message.error(result.error?.message ?? "Ошибка отправки в 1С");
      } else if (result.status === "already_exported") {
        message.info("Заявка уже была экспортирована в 1С");
      } else {
        message.success(result.one_c_enabled === false ? "Отправлено в fake 1С" : "Заявка отправлена в 1С");
      }
      await Promise.all([registryQuery.refetch(), metricsQuery.refetch()]);
    },
    onError: (error) => message.error(apiError(error, "Ошибка отправки в 1С")),
  });

  const applyFilters = (values: FilterValues) => {
    setFilters({
      approval_status: "Approved",
      export_status: values.export_status,
      organization_id: values.organization_id,
      counterparty_id: values.counterparty_id,
      project_id: values.project_id,
      search: values.search?.trim() || undefined,
      amount_from: values.amount_from,
      amount_to: values.amount_to,
      date_from: values.date_range?.[0]?.format("YYYY-MM-DD"),
      date_to: values.date_range?.[1]?.format("YYYY-MM-DD"),
      limit: filters.limit ?? 50,
      offset: 0,
      sort_by: filters.sort_by ?? "approved_at",
      sort_order: filters.sort_order ?? "desc",
    });
  };

  const resetFilters = () => {
    form.resetFields();
    setFilters({ approval_status: "Approved", limit: 50, offset: 0, sort_by: "approved_at", sort_order: "desc" });
  };

  const dictionaryOptions = (items?: AccountingDictionaryItem[]) => (items ?? []).map((item) => ({ value: item.id, label: item.code ? `${item.code} - ${item.name}` : item.name }));

  const triggerSend = (row: TreasuryPaymentRequest, force: boolean) => {
    if (force) {
      modal.confirm({
        title: "Повторить отправку в 1С?",
        content: "Будет выполнена принудительная повторная отправка с force=true.",
        okText: "Повторить",
        cancelText: "Отмена",
        onOk: async () => sendMutation.mutateAsync({ documentId: row.document_id, force: true }),
      });
      return;
    }
    sendMutation.mutate({ documentId: row.document_id, force: false });
  };

  const columns = [
      { title: "Номер", dataIndex: "number", render: (value: string, row: TreasuryPaymentRequest) => <Link to={`/documents/${row.document_id}`}>{value}</Link> },
      { title: "Дата", dataIndex: "document_date", render: (value?: string | null) => (value ? dayjs(value).format("DD.MM.YYYY") : "-") },
      { title: "Одобрено", dataIndex: "approved_at", render: (value?: string | null) => (value ? dayjs(value).format("DD.MM.YYYY HH:mm") : "-") },
      { title: "Организация", render: (_: unknown, row: TreasuryPaymentRequest) => row.organization?.name ?? "-" },
      { title: "Контрагент", render: (_: unknown, row: TreasuryPaymentRequest) => row.counterparty?.name ?? "-" },
      { title: "Договор", render: (_: unknown, row: TreasuryPaymentRequest) => row.contract?.name ?? "-" },
      { title: "Проект", render: (_: unknown, row: TreasuryPaymentRequest) => row.project?.code ?? row.project?.name ?? "-" },
      { title: "Сумма", dataIndex: "amount", render: (value?: number | null) => (value != null ? metricCurrency(value) : "-") },
      { title: "Валюта", render: (_: unknown, row: TreasuryPaymentRequest) => row.currency?.code ?? "-" },
      {
        title: "Статус 1С",
        render: (_: unknown, row: TreasuryPaymentRequest) => {
          const status = row.export?.status ?? "not_exported";
          const meta = exportStatusMeta[status] ?? { label: status, color: "default" };
          return <Tag color={meta.color}>{meta.label}</Tag>;
        },
      },
      {
        title: "Платежное поручение",
        render: (_: unknown, row: TreasuryPaymentRequest) => row.export?.one_c_payment_order_number ?? row.export?.one_c_payment_order_external_id ?? "-",
      },
      {
        title: "Действия",
        render: (_: unknown, row: TreasuryPaymentRequest) => {
          const status = row.export?.status ?? "not_exported";
          return (
            <Space wrap>
              <Button size="small"><Link to={`/documents/${row.document_id}`}>Открыть</Link></Button>
              {canReadIntegrationLogs ? (
                <Button size="small"><Link to={`/integration/logs?document_id=${encodeURIComponent(row.document_id)}`}>Журнал</Link></Button>
              ) : null}
              {canSend && ["not_exported", "Failed"].includes(status) ? (
                <Button size="small" type="primary" loading={sendMutation.isPending} onClick={() => triggerSend(row, false)}>
                  Отправить в 1С
                </Button>
              ) : null}
              {canSend && ["CreatedIn1C", "AlreadyExistsIn1C"].includes(status) ? (
                <Button size="small" loading={sendMutation.isPending} onClick={() => triggerSend(row, true)}>
                  Повторить
                </Button>
              ) : null}
              {status === "Failed" ? (
                <Button size="small" danger icon={<ExclamationCircleOutlined />} onClick={() => setErrorRow(row)}>
                  Ошибка
                </Button>
              ) : null}
            </Space>
          );
        },
      },
    ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {modalContextHolder}
      <div>
        <Typography.Title level={4} style={{ margin: 0 }}>Казначейство</Typography.Title>
        <Typography.Text type="secondary">Реестр согласованных заявок на оплату и отправки в 1С</Typography.Text>
      </div>

      {registryQuery.isError || metricsQuery.isError ? (
        <Alert type="error" showIcon message={apiError(registryQuery.error ?? metricsQuery.error, "Ошибка загрузки реестра казначейства")} />
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="Готово к отправке" value={metricsQuery.data?.ready_to_send ?? 0} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="Создано в 1С" value={metricsQuery.data?.created_in_1c ?? 0} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="Уже было в 1С" value={metricsQuery.data?.already_exists_in_1c ?? 0} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="Ошибки" value={metricsQuery.data?.failed ?? 0} /></Card></Col>
        <Col xs={24} sm={12} lg={12}><Card><Statistic title="Сумма готовых к отправке" value={metricCurrency(metricsQuery.data?.total_amount_ready ?? 0)} /></Card></Col>
        <Col xs={24} sm={12} lg={12}><Card><Statistic title="Сумма созданных в 1С" value={metricCurrency(metricsQuery.data?.total_amount_created_in_1c ?? 0)} /></Card></Col>
      </Row>

      <Card>
        <Form form={form} layout="vertical" onFinish={applyFilters}>
          <Row gutter={[16, 8]}>
            <Col xs={24} md={8} lg={6}>
              <Form.Item name="export_status" label="Статус 1С">
                <Select allowClear options={exportStatusOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={6}>
              <Form.Item name="organization_id" label="Организация">
                <Select allowClear showSearch options={dictionaryOptions(organizationsQuery.data)} optionFilterProp="label" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={6}>
              <Form.Item name="counterparty_id" label="Контрагент">
                <Select allowClear showSearch options={dictionaryOptions(counterpartiesQuery.data)} optionFilterProp="label" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={6}>
              <Form.Item name="project_id" label="Проект">
                <Select allowClear showSearch options={dictionaryOptions(projectsQuery.data)} optionFilterProp="label" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={6}>
              <Form.Item name="date_range" label="Период документа">
                <RangePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={4}>
              <Form.Item name="amount_from" label="Сумма от">
                <InputNumber style={{ width: "100%" }} min={0} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={4}>
              <Form.Item name="amount_to" label="Сумма до">
                <InputNumber style={{ width: "100%" }} min={0} />
              </Form.Item>
            </Col>
            <Col xs={24} lg={10}>
              <Form.Item name="search" label="Поиск">
                <Input placeholder="Номер или заголовок" />
              </Form.Item>
            </Col>
          </Row>
          <Space>
            <Button type="primary" htmlType="submit">Применить</Button>
            <Button onClick={resetFilters}>Сбросить</Button>
          </Space>
        </Form>
      </Card>

      <Card>
        <Table<TreasuryPaymentRequest>
          rowKey="document_id"
          loading={registryQuery.isLoading}
          dataSource={registryQuery.data?.items ?? []}
          pagination={{
            total: registryQuery.data?.total ?? 0,
            pageSize: filters.limit ?? 50,
            current: Math.floor((filters.offset ?? 0) / (filters.limit ?? 50)) + 1,
            onChange: (page, pageSize) => {
              setFilters((prev) => ({ ...prev, offset: (page - 1) * pageSize, limit: pageSize }));
            },
          }}
          columns={columns}
        />
      </Card>

      <Modal open={Boolean(errorRow)} title="Ошибка отправки в 1С" footer={null} onCancel={() => setErrorRow(null)}>
        {errorRow ? (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="Документ">{errorRow.number}</Descriptions.Item>
            <Descriptions.Item label="Код ошибки">{errorRow.export?.error_code ?? "-"}</Descriptions.Item>
            <Descriptions.Item label="Сообщение">{errorRow.export?.error_message ?? "-"}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </Space>
  );
};
