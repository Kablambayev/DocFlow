import { PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, DatePicker, Form, Input, Modal, Row, Select, Space, Table, Tag, Typography, message } from "antd";
import type { Dayjs } from "dayjs";
import dayjs from "dayjs";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getCurrencies, getOrganizations } from "../../entities/accounting";
import type { AccountingDictionaryItem } from "../../entities/accounting";
import { createPaymentRegister, getPaymentRegisters } from "../../entities/payment-register";
import type { PaymentRegister, PaymentRegisterCreatePayload, PaymentRegisterQueryParams } from "../../entities/payment-register";
import { useAuth } from "../../shared/auth/useAuth";

const { RangePicker } = DatePicker;

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const registerStatusMeta: Record<string, { label: string; color: string }> = {
  Draft: { label: "Черновик", color: "default" },
  ReadyToSend: { label: "Готов к отправке", color: "gold" },
  Sending: { label: "Отправляется", color: "blue" },
  PartiallySent: { label: "Частично отправлен", color: "orange" },
  Sent: { label: "Отправлен", color: "green" },
  Failed: { label: "Ошибка", color: "red" },
  Cancelled: { label: "Отменен", color: "default" },
};

const registerStatusOptions = Object.entries(registerStatusMeta).map(([value, meta]) => ({ value, label: meta.label }));

type FilterValues = {
  status?: string;
  organization_id?: string;
  currency_id?: string;
  search?: string;
  date_range?: [Dayjs, Dayjs];
};

type CreateFormValues = {
  number?: string;
  date: Dayjs;
  organization_id?: string;
  currency_id?: string;
  comment?: string;
};

const money = (value?: number | null) => new Intl.NumberFormat("ru-RU").format(value ?? 0);

export const PaymentRegistersPage = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const [filtersForm] = Form.useForm<FilterValues>();
  const [createForm] = Form.useForm<CreateFormValues>();
  const [filters, setFilters] = useState<PaymentRegisterQueryParams>({ limit: 50, offset: 0, sort_by: "date", sort_order: "desc" });
  const [createOpen, setCreateOpen] = useState(false);
  const canManage = hasPermission("payment_register.manage");

  const organizationsQuery = useQuery({ queryKey: ["accounting", "organizations", "payment-registers"], queryFn: () => getOrganizations({ is_active: true, limit: 200 }) });
  const currenciesQuery = useQuery({ queryKey: ["accounting", "currencies", "payment-registers"], queryFn: () => getCurrencies({ is_active: true, limit: 200 }) });
  const registersQuery = useQuery({ queryKey: ["payment-registers", filters], queryFn: () => getPaymentRegisters(filters) });

  const createMutation = useMutation({
    mutationFn: (payload: PaymentRegisterCreatePayload) => createPaymentRegister(payload),
    onSuccess: (result) => {
      message.success("Реестр оплат создан");
      setCreateOpen(false);
      createForm.resetFields();
      void registersQuery.refetch();
      navigate(`/payment-registers/${result.id}`);
    },
    onError: (error) => message.error(apiError(error, "Не удалось создать реестр оплат")),
  });

  const dictionaryOptions = (items?: AccountingDictionaryItem[]) => (items ?? []).map((item) => ({ value: item.id, label: item.code ? `${item.code} — ${item.name}` : item.name }));

  const applyFilters = (values: FilterValues) => {
    setFilters((prev) => ({
      ...prev,
      status: values.status,
      organization_id: values.organization_id,
      currency_id: values.currency_id,
      search: values.search?.trim() || undefined,
      date_from: values.date_range?.[0]?.format("YYYY-MM-DD"),
      date_to: values.date_range?.[1]?.format("YYYY-MM-DD"),
      offset: 0,
    }));
  };

  const resetFilters = () => {
    filtersForm.resetFields();
    setFilters({ limit: 50, offset: 0, sort_by: "date", sort_order: "desc" });
  };

  const submitCreate = async () => {
    const values = await createForm.validateFields();
    createMutation.mutate({
      number: values.number?.trim() || undefined,
      date: values.date.format("YYYY-MM-DD"),
      organization_id: values.organization_id ?? null,
      currency_id: values.currency_id ?? null,
      comment: values.comment?.trim() || null,
    });
  };

  const columns = [
    { title: "Номер", dataIndex: "number", render: (value: string, row: PaymentRegister) => <Link to={`/payment-registers/${row.id}`}>{value}</Link> },
    { title: "Дата", dataIndex: "date", render: (value: string) => dayjs(value).format("DD.MM.YYYY") },
    {
      title: "Статус",
      dataIndex: "status",
      render: (value: string) => {
        const meta = registerStatusMeta[value] ?? { label: value, color: "default" };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    { title: "Организация", render: (_: unknown, row: PaymentRegister) => row.organization?.name ?? "-" },
    { title: "Валюта", render: (_: unknown, row: PaymentRegister) => row.currency?.code ?? row.currency?.name ?? "-" },
    { title: "Сумма", dataIndex: "total_amount", render: (value: number) => money(value) },
    { title: "Строк", dataIndex: "rows_count" },
    { title: "Успешно", dataIndex: "sent_rows_count" },
    { title: "Ошибок", dataIndex: "failed_rows_count" },
    { title: "Комментарий", dataIndex: "comment", ellipsis: true },
    { title: "Действия", render: (_: unknown, row: PaymentRegister) => <Button size="small"><Link to={`/payment-registers/${row.id}`}>Открыть</Link></Button> },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
        <div>
          <Typography.Title level={4} style={{ margin: 0 }}>Реестры оплат</Typography.Title>
          <Typography.Text type="secondary">Групповая отправка согласованных заявок на оплату в 1С</Typography.Text>
        </div>
        {canManage ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setCreateOpen(true); createForm.setFieldsValue({ date: dayjs() }); }}>
            Создать реестр
          </Button>
        ) : null}
      </div>

      {registersQuery.isError ? <Alert type="error" showIcon message={apiError(registersQuery.error, "Не удалось загрузить реестры оплат")} /> : null}

      <Card>
        <Form form={filtersForm} layout="vertical" onFinish={applyFilters}>
          <Row gutter={[16, 8]}>
            <Col xs={24} md={8} lg={5}>
              <Form.Item name="status" label="Статус">
                <Select allowClear options={registerStatusOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={7}>
              <Form.Item name="organization_id" label="Организация">
                <Select allowClear showSearch options={dictionaryOptions(organizationsQuery.data)} optionFilterProp="label" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8} lg={4}>
              <Form.Item name="currency_id" label="Валюта">
                <Select allowClear showSearch options={dictionaryOptions(currenciesQuery.data)} optionFilterProp="label" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={4}>
              <Form.Item name="date_range" label="Период">
                <RangePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={8}>
              <Form.Item name="search" label="Поиск">
                <Input placeholder="Номер или комментарий" />
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
        <Table<PaymentRegister>
          rowKey="id"
          loading={registersQuery.isLoading}
          dataSource={registersQuery.data?.items ?? []}
          columns={columns}
          pagination={{
            total: registersQuery.data?.total ?? 0,
            pageSize: filters.limit ?? 50,
            current: Math.floor((filters.offset ?? 0) / (filters.limit ?? 50)) + 1,
            onChange: (page, pageSize) => setFilters((prev) => ({ ...prev, offset: (page - 1) * pageSize, limit: pageSize })),
          }}
        />
      </Card>

      <Modal
        open={createOpen}
        title="Новый реестр оплат"
        onCancel={() => setCreateOpen(false)}
        onOk={() => void submitCreate()}
        confirmLoading={createMutation.isPending}
        okText="Создать"
        cancelText="Отмена"
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="number" label="Номер">
            <Input placeholder="Если пусто — сформируется автоматически" />
          </Form.Item>
          <Form.Item name="date" label="Дата" rules={[{ required: true, message: "Укажите дату" }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="organization_id" label="Организация">
            <Select allowClear showSearch options={dictionaryOptions(organizationsQuery.data)} optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="currency_id" label="Валюта">
            <Select allowClear showSearch options={dictionaryOptions(currenciesQuery.data)} optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="comment" label="Комментарий">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};
