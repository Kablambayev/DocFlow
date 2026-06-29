import { ApiOutlined, ReloadOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, DatePicker, Descriptions, Drawer, Form, Input, Modal, Row, Select, Space, Table, Tag, Typography, message } from "antd";
import type { Dayjs } from "dayjs";
import dayjs from "dayjs";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getIntegrationLogDetail, getIntegrationLogs, retryIntegrationLog } from "../../entities/integration-log";
import type { IntegrationLogDetail, IntegrationLogListItem, IntegrationLogQueryParams } from "../../entities/integration-log";
import { useAuth } from "../../shared/auth/useAuth";

const { RangePicker } = DatePicker;

type FilterValues = {
  direction?: "Inbound" | "Outbound";
  operation_type?: string;
  status?: string;
  search?: string;
  date_range?: [Dayjs, Dayjs];
};

const operationOptions = [
  { value: "1c_test_connection", label: "Проверка подключения к 1С" },
  { value: "1c_import_organizations", label: "Импорт организаций" },
  { value: "1c_import_counterparties", label: "Импорт контрагентов" },
  { value: "1c_import_currencies", label: "Импорт валют" },
  { value: "1c_import_expense_items", label: "Импорт статей затрат" },
  { value: "1c_import_counterparty_contracts", label: "Импорт договоров контрагентов" },
  { value: "1c_export_payment_request", label: "Экспорт заявки на оплату" },
];

const statusOptions = [
  { value: "Started", label: "Started" },
  { value: "Success", label: "Success" },
  { value: "PartialSuccess", label: "PartialSuccess" },
  { value: "Failed", label: "Failed" },
  { value: "Skipped", label: "Skipped" },
];

const statusMeta: Record<string, { color: string; label: string }> = {
  Started: { color: "blue", label: "Started" },
  Success: { color: "green", label: "Success" },
  PartialSuccess: { color: "orange", label: "PartialSuccess" },
  Failed: { color: "red", label: "Failed" },
  Skipped: { color: "default", label: "Skipped" },
};

const directionMeta: Record<string, { color: string; label: string }> = {
  Inbound: { color: "geekblue", label: "Inbound" },
  Outbound: { color: "cyan", label: "Outbound" },
};

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const prettyJson = (value: unknown) => JSON.stringify(value ?? {}, null, 2);

const directionValues = new Set(["Inbound", "Outbound"]);

const readInitialFilters = (searchParams: URLSearchParams): IntegrationLogQueryParams => {
  const direction = searchParams.get("direction");
  return {
    document_id: searchParams.get("document_id") || undefined,
    direction: direction && directionValues.has(direction) ? (direction as "Inbound" | "Outbound") : undefined,
    operation_type: searchParams.get("operation_type") || undefined,
    status: searchParams.get("status") || undefined,
    limit: 50,
    offset: 0,
    sort_by: "created_at",
    sort_order: "desc",
  };
};

export const IntegrationLogsPage = () => {
  const { hasPermission } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [form] = Form.useForm<FilterValues>();
  const [modal, modalContextHolder] = Modal.useModal();
  const [filters, setFilters] = useState<IntegrationLogQueryParams>(() => readInitialFilters(searchParams));
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const canRetry = hasPermission("integration_1c.payment_request.send");

  const logsQuery = useQuery({
    queryKey: ["integration-logs", filters],
    queryFn: () => getIntegrationLogs(filters),
  });

  const detailQuery = useQuery({
    queryKey: ["integration-log-detail", selectedLogId],
    queryFn: () => getIntegrationLogDetail(selectedLogId as string),
    enabled: Boolean(selectedLogId),
  });

  const retryMutation = useMutation({
    mutationFn: retryIntegrationLog,
    onSuccess: async () => {
      message.success("Повторная отправка запущена");
      await Promise.all([logsQuery.refetch(), detailQuery.refetch()]);
    },
    onError: (error) => {
      message.error(apiError(error, "Не удалось повторить операцию"));
    },
  });

  const applyFilters = (values: FilterValues) => {
    setFilters((prev) => ({
      ...prev,
      direction: values.direction,
      operation_type: values.operation_type,
      status: values.status,
      search: values.search?.trim() || undefined,
      date_from: values.date_range?.[0]?.toISOString(),
      date_to: values.date_range?.[1]?.toISOString(),
      offset: 0,
    }));
  };

  const resetFilters = () => {
    form.resetFields();
    setSearchParams({});
    setFilters({
      limit: 50,
      offset: 0,
      sort_by: "created_at",
      sort_order: "desc",
    });
  };

  const triggerRetry = (log: IntegrationLogListItem) => {
    modal.confirm({
      title: "Повторить отправку в 1С?",
      content: "Будет вызвана принудительная повторная отправка PaymentRequest с force=true.",
      okText: "Повторить",
      cancelText: "Отмена",
      onOk: async () => retryMutation.mutateAsync(log.id),
    });
  };

  const isRetrySupported = (log: IntegrationLogListItem) =>
    canRetry && log.direction === "Outbound" && log.operation_type === "1c_export_payment_request";

  const selectedLog: IntegrationLogDetail | undefined = detailQuery.data;

  const columns = [
    {
      title: "Дата",
      dataIndex: "created_at",
      render: (value: string) => dayjs(value).format("DD.MM.YYYY HH:mm:ss"),
    },
    {
      title: "Направление",
      render: (_: unknown, row: IntegrationLogListItem) => {
        const meta = directionMeta[row.direction] ?? { color: "default", label: row.direction };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    {
      title: "Операция",
      dataIndex: "operation_type",
      render: (value: string) => operationOptions.find((item) => item.value === value)?.label ?? value,
    },
    {
      title: "Статус",
      dataIndex: "status",
      render: (value: string) => {
        const meta = statusMeta[value] ?? { color: "default", label: value };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    {
      title: "Документ",
      render: (_: unknown, row: IntegrationLogListItem) =>
        row.document_id && row.document_number ? <Link to={`/documents/${row.document_id}`}>{row.document_number}</Link> : row.document_number ?? "—",
    },
    {
      title: "HTTP",
      render: (_: unknown, row: IntegrationLogListItem) => row.response_status_code ?? "-",
    },
    {
      title: "Длительность",
      render: (_: unknown, row: IntegrationLogListItem) => (row.duration_ms != null ? `${row.duration_ms} ms` : "-"),
    },
    {
      title: "Ошибка",
      render: (_: unknown, row: IntegrationLogListItem) => row.error_code ?? row.error_message ?? "-",
    },
    {
      title: "Correlation ID",
      dataIndex: "correlation_id",
      render: (value?: string | null) => value ?? "-",
    },
    {
      title: "Действия",
      render: (_: unknown, row: IntegrationLogListItem) => (
        <Space wrap>
          <Button size="small" onClick={() => setSelectedLogId(row.id)}>
            Открыть детали
          </Button>
          {row.document_id ? (
            <Button size="small">
              <Link to={`/documents/${row.document_id}`}>Открыть документ</Link>
            </Button>
          ) : null}
          {isRetrySupported(row) ? (
            <Button size="small" type="primary" icon={<ReloadOutlined />} loading={retryMutation.isPending} onClick={() => triggerRetry(row)}>
              Повторить
            </Button>
          ) : null}
        </Space>
      ),
    },
  ];

  const renderJsonBlock = (value: unknown) => (
    <pre
      style={{
        margin: 0,
        padding: 12,
        borderRadius: 8,
        background: "#f6f8fa",
        overflowX: "auto",
        maxWidth: "100%",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
    >
      {prettyJson(value)}
    </pre>
  );

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {modalContextHolder}
      <div>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Журнал обмена с 1С
        </Typography.Title>
        <Typography.Text type="secondary">Технический журнал входящих и исходящих HTTP-операций интеграции</Typography.Text>
      </div>

      {logsQuery.isError ? (
        <Alert type="error" showIcon message={apiError(logsQuery.error, "Не удалось загрузить журнал обмена")} />
      ) : null}

      {filters.document_id ? (
        <Alert
          type="info"
          showIcon
          message="Журнал отфильтрован по документу"
          description={<Typography.Text copyable>{filters.document_id}</Typography.Text>}
          action={<Button onClick={resetFilters}>Сбросить фильтр</Button>}
        />
      ) : null}

      <Card>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            direction: filters.direction,
            operation_type: filters.operation_type,
            status: filters.status,
          }}
          onFinish={applyFilters}
        >
          <Row gutter={[16, 8]}>
            <Col xs={24} md={8} lg={6}>
              <Form.Item name="direction" label="Направление">
                <Select allowClear options={[{ value: "Inbound", label: "Inbound" }, { value: "Outbound", label: "Outbound" }]} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={8}>
              <Form.Item name="operation_type" label="Операция">
                <Select allowClear showSearch optionFilterProp="label" options={operationOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={5}>
              <Form.Item name="status" label="Статус">
                <Select allowClear options={statusOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={5}>
              <Form.Item name="date_range" label="Период">
                <RangePicker style={{ width: "100%" }} showTime />
              </Form.Item>
            </Col>
            <Col xs={24} lg={10}>
              <Form.Item name="search" label="Поиск">
                <Input placeholder="Correlation ID, idempotency key, код ошибки, URL..." />
              </Form.Item>
            </Col>
          </Row>
          <Space>
            <Button type="primary" htmlType="submit" icon={<ApiOutlined />}>
              Применить
            </Button>
            <Button onClick={resetFilters}>Сбросить</Button>
          </Space>
        </Form>
      </Card>

      <Card>
        <Table<IntegrationLogListItem>
          rowKey="id"
          loading={logsQuery.isLoading}
          dataSource={logsQuery.data?.items ?? []}
          columns={columns}
          pagination={{
            total: logsQuery.data?.total ?? 0,
            pageSize: filters.limit ?? 50,
            current: Math.floor((filters.offset ?? 0) / (filters.limit ?? 50)) + 1,
            onChange: (page, pageSize) => {
              setFilters((prev) => ({ ...prev, offset: (page - 1) * pageSize, limit: pageSize }));
            },
          }}
        />
      </Card>

      <Drawer title="Детали операции интеграции" width={720} styles={{ body: { overflowX: "hidden" } }} open={Boolean(selectedLogId)} onClose={() => setSelectedLogId(null)} destroyOnHidden>
        {detailQuery.isError ? <Alert type="error" showIcon message={apiError(detailQuery.error, "Не удалось загрузить детали")} /> : null}
        {selectedLog ? (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Card size="small" title="Общее">
              <Descriptions size="small" bordered column={1}>
                <Descriptions.Item label="Направление">{selectedLog.direction}</Descriptions.Item>
                <Descriptions.Item label="Операция">{selectedLog.operation_type}</Descriptions.Item>
                <Descriptions.Item label="Статус">{selectedLog.status}</Descriptions.Item>
                <Descriptions.Item label="Документ">{selectedLog.document_number ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Инициатор">{selectedLog.initiated_by_name ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Создано">{dayjs(selectedLog.created_at).format("DD.MM.YYYY HH:mm:ss")}</Descriptions.Item>
                <Descriptions.Item label="Длительность">{selectedLog.duration_ms != null ? `${selectedLog.duration_ms} ms` : "-"}</Descriptions.Item>
                <Descriptions.Item label="Correlation ID">{selectedLog.correlation_id ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Idempotency key">{selectedLog.idempotency_key ?? "-"}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="Request">
              <Descriptions size="small" bordered column={1}>
                <Descriptions.Item label="URL">{selectedLog.request_url ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Method">{selectedLog.request_method ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Headers">{renderJsonBlock(selectedLog.request_headers)}</Descriptions.Item>
                <Descriptions.Item label="Payload">{renderJsonBlock(selectedLog.request_payload)}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="Response">
              <Descriptions size="small" bordered column={1}>
                <Descriptions.Item label="HTTP status">{selectedLog.response_status_code ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Headers">{renderJsonBlock(selectedLog.response_headers)}</Descriptions.Item>
                <Descriptions.Item label="Payload">{renderJsonBlock(selectedLog.response_payload)}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="Ошибка">
              <Descriptions size="small" bordered column={1}>
                <Descriptions.Item label="Код">{selectedLog.error_code ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Сообщение">{selectedLog.error_message ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Details">{renderJsonBlock(selectedLog.error_details)}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="Технические данные">
              <Descriptions size="small" bordered column={1}>
                <Descriptions.Item label="Entity type">{selectedLog.entity_type ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Entity id">{selectedLog.entity_id ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Updated at">{selectedLog.updated_at ? dayjs(selectedLog.updated_at).format("DD.MM.YYYY HH:mm:ss") : "-"}</Descriptions.Item>
              </Descriptions>
            </Card>

            {isRetrySupported(selectedLog) ? (
              <Button type="primary" icon={<ReloadOutlined />} loading={retryMutation.isPending} onClick={() => triggerRetry(selectedLog)}>
                Повторить отправку
              </Button>
            ) : null}
          </Space>
        ) : null}
      </Drawer>
    </Space>
  );
};
