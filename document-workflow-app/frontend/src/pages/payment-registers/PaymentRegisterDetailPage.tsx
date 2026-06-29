import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Checkbox, DatePicker, Descriptions, Form, Input, Modal, Select, Space, Table, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getCurrencies, getOrganizations } from "../../entities/accounting";
import type { AccountingDictionaryItem } from "../../entities/accounting";
import {
  addPaymentRegisterRows,
  cancelPaymentRegister,
  deletePaymentRegister,
  getAvailablePaymentRequests,
  getPaymentRegister,
  markPaymentRegisterReady,
  removePaymentRegisterRow,
  sendPaymentRegisterTo1C,
  updatePaymentRegister,
} from "../../entities/payment-register";
import type { AvailablePaymentRequest, PaymentRegisterRow } from "../../entities/payment-register";
import { useAuth } from "../../shared/auth/useAuth";

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

const exportStatusMeta: Record<string, { label: string; color: string }> = {
  Pending: { label: "В очереди", color: "blue" },
  Sent: { label: "Отправлено", color: "blue" },
  CreatedIn1C: { label: "Создано в 1С", color: "green" },
  AlreadyExistsIn1C: { label: "Уже было в 1С", color: "green" },
  Failed: { label: "Ошибка", color: "red" },
};

const money = (value?: number | null) => new Intl.NumberFormat("ru-RU").format(value ?? 0);

export const PaymentRegisterDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const [editForm] = Form.useForm();
  const [selection, setSelection] = useState<string[]>([]);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [includeFailed, setIncludeFailed] = useState(false);
  const [availableSearch, setAvailableSearch] = useState("");
  const canManage = hasPermission("payment_register.manage");
  const canSend = hasPermission("payment_register.send");
  const registerId = id ?? "";

  const registerQuery = useQuery({
    queryKey: ["payment-register", registerId],
    queryFn: () => getPaymentRegister(registerId),
    enabled: Boolean(registerId),
  });
  const register = registerQuery.data;

  const organizationsQuery = useQuery({ queryKey: ["accounting", "organizations", "payment-register-detail"], queryFn: () => getOrganizations({ is_active: true, limit: 200 }) });
  const currenciesQuery = useQuery({ queryKey: ["accounting", "currencies", "payment-register-detail"], queryFn: () => getCurrencies({ is_active: true, limit: 200 }) });

  const availableQuery = useQuery({
    queryKey: ["payment-register", registerId, "available", register?.organization?.id, register?.currency?.id, includeFailed, availableSearch],
    queryFn: () =>
      getAvailablePaymentRequests({
        organization_id: register?.organization?.id,
        currency_id: register?.currency?.id,
        include_failed_exports: includeFailed,
        search: availableSearch.trim() || undefined,
        limit: 100,
        offset: 0,
      }),
    enabled: addModalOpen,
  });

  const dictionaryOptions = (items?: AccountingDictionaryItem[]) => (items ?? []).map((item) => ({ value: item.id, label: item.code ? `${item.code} — ${item.name}` : item.name }));

  const refreshRegister = async () => {
    await registerQuery.refetch();
  };

  const updateMutation = useMutation({
    mutationFn: (payload: { number?: string; date?: string; organization_id?: string | null; currency_id?: string | null; comment?: string | null }) => updatePaymentRegister(registerId, payload),
    onSuccess: async () => {
      message.success("Реестр обновлен");
      await refreshRegister();
    },
    onError: (error) => message.error(apiError(error, "Не удалось обновить реестр")),
  });

  const addRowsMutation = useMutation({
    mutationFn: (documentIds: string[]) => addPaymentRegisterRows(registerId, documentIds),
    onSuccess: async (result) => {
      message.success(`Добавлено строк: ${result.added_count}`);
      if (result.errors.length > 0) {
        message.warning(`Не добавлено: ${result.errors.length}`);
      }
      setSelection([]);
      setAddModalOpen(false);
      await refreshRegister();
    },
    onError: (error) => message.error(apiError(error, "Не удалось добавить строки")),
  });

  const removeRowMutation = useMutation({
    mutationFn: (rowId: string) => removePaymentRegisterRow(registerId, rowId),
    onSuccess: async () => {
      message.success("Строка удалена");
      await refreshRegister();
    },
    onError: (error) => message.error(apiError(error, "Не удалось удалить строку")),
  });

  const markReadyMutation = useMutation({
    mutationFn: () => markPaymentRegisterReady(registerId),
    onSuccess: async () => {
      message.success("Реестр переведен в статус «Готов к отправке»");
      await refreshRegister();
    },
    onError: (error) => message.error(apiError(error, "Не удалось перевести реестр в готовность")),
  });

  const sendMutation = useMutation({
    mutationFn: (force: boolean) => sendPaymentRegisterTo1C(registerId, force),
    onSuccess: async (result) => {
      message.success(`Обработано строк: ${result.processed_rows_count}, пропущено: ${result.skipped_rows_count}`);
      await refreshRegister();
    },
    onError: (error) => message.error(apiError(error, "Не удалось отправить реестр в 1С")),
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelPaymentRegister(registerId),
    onSuccess: async () => {
      message.success("Реестр отменен");
      await refreshRegister();
    },
    onError: (error) => message.error(apiError(error, "Не удалось отменить реестр")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deletePaymentRegister(registerId),
    onSuccess: () => {
      message.success("Реестр удален");
      navigate("/payment-registers");
    },
    onError: (error) => message.error(apiError(error, "Не удалось удалить реестр")),
  });

  const statusTag = useMemo(() => {
    const meta = register ? registerStatusMeta[register.status] ?? { label: register.status, color: "default" } : null;
    return meta ? <Tag color={meta.color}>{meta.label}</Tag> : null;
  }, [register]);

  const rowColumns = [
    { title: "#", dataIndex: "row_number", width: 72 },
    { title: "Заявка", render: (_: unknown, row: PaymentRegisterRow) => <Link to={`/documents/${row.document_id}`}>{row.document_number ?? row.document_id}</Link> },
    { title: "Контрагент", render: (_: unknown, row: PaymentRegisterRow) => row.counterparty?.name ?? "-" },
    { title: "Договор", render: (_: unknown, row: PaymentRegisterRow) => row.contract?.number ?? row.contract?.name ?? "-" },
    { title: "Сумма", dataIndex: "amount", render: (value: number) => money(value) },
    { title: "Назначение платежа", dataIndex: "payment_purpose", ellipsis: true },
    {
      title: "Статус экспорта",
      render: (_: unknown, row: PaymentRegisterRow) => {
        const status = row.export?.status;
        if (!status) return <Tag>Не отправлено</Tag>;
        const meta = exportStatusMeta[status] ?? { label: status, color: "default" };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    { title: "Платежное поручение", render: (_: unknown, row: PaymentRegisterRow) => row.export?.one_c_payment_order_number ?? row.export?.one_c_payment_order_external_id ?? "-" },
    {
      title: "Действия",
      render: (_: unknown, row: PaymentRegisterRow) =>
        register?.status === "Draft" && canManage ? (
          <Button size="small" danger icon={<DeleteOutlined />} loading={removeRowMutation.isPending} onClick={() => removeRowMutation.mutate(row.id)}>
            Удалить
          </Button>
        ) : null,
    },
  ];

  const availableColumns = [
    { title: "Номер", dataIndex: "number" },
    { title: "Дата", dataIndex: "document_date", render: (value?: string | null) => (value ? dayjs(value).format("DD.MM.YYYY") : "-") },
    { title: "Организация", render: (_: unknown, row: AvailablePaymentRequest) => row.organization?.name ?? "-" },
    { title: "Контрагент", render: (_: unknown, row: AvailablePaymentRequest) => row.counterparty?.name ?? "-" },
    { title: "Сумма", dataIndex: "amount", render: (value?: number | null) => money(value) },
    { title: "Валюта", render: (_: unknown, row: AvailablePaymentRequest) => row.currency?.code ?? "-" },
    {
      title: "История экспорта",
      render: (_: unknown, row: AvailablePaymentRequest) => {
        if (!row.export_status) return <Tag>Не отправлялось</Tag>;
        const meta = exportStatusMeta[row.export_status] ?? { label: row.export_status, color: "default" };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
  ];

  const canEditHeader = canManage && register?.status === "Draft";
  const canAddRows = canManage && register?.status === "Draft";
  const canMarkReady = canManage && register?.status === "Draft";
  const canCancel = canManage && ["Draft", "ReadyToSend", "Failed", "PartiallySent"].includes(register?.status ?? "");
  const canDelete = canManage && register?.status === "Draft";
  const canSendNow = canSend && ["ReadyToSend", "PartiallySent", "Failed"].includes(register?.status ?? "");

  const submitHeaderUpdate = async () => {
    const values = await editForm.validateFields();
    updateMutation.mutate({
      number: values.number?.trim() || undefined,
      date: values.date?.format("YYYY-MM-DD"),
      organization_id: values.organization_id ?? null,
      currency_id: values.currency_id ?? null,
      comment: values.comment?.trim() || null,
    });
  };

  if (!registerId) {
    return <Alert type="error" showIcon message="Не указан идентификатор реестра" />;
  }

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
        <div>
          <Typography.Title level={4} style={{ margin: 0 }}>{register?.number ?? "Реестр оплат"}</Typography.Title>
          <Space>{statusTag}</Space>
        </div>
        <Space wrap>
          <Button onClick={() => navigate("/payment-registers")}>Назад к списку</Button>
          {canAddRows ? <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>Добавить строки</Button> : null}
          {canMarkReady ? <Button onClick={() => markReadyMutation.mutate()} loading={markReadyMutation.isPending}>Готов к отправке</Button> : null}
          {canSendNow ? <Button type="primary" onClick={() => sendMutation.mutate(false)} loading={sendMutation.isPending}>Отправить в 1С</Button> : null}
          {canSendNow ? <Button onClick={() => sendMutation.mutate(true)} loading={sendMutation.isPending}>Отправить повторно</Button> : null}
          {canCancel ? <Button danger onClick={() => cancelMutation.mutate()} loading={cancelMutation.isPending}>Отменить</Button> : null}
          {canDelete ? <Button danger onClick={() => deleteMutation.mutate()} loading={deleteMutation.isPending}>Удалить</Button> : null}
        </Space>
      </div>

      {registerQuery.isError ? <Alert type="error" showIcon message={apiError(registerQuery.error, "Не удалось загрузить реестр оплат")} /> : null}

      <Card loading={registerQuery.isLoading}>
        {register ? (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Дата">{dayjs(register.date).format("DD.MM.YYYY")}</Descriptions.Item>
              <Descriptions.Item label="Статус">{statusTag}</Descriptions.Item>
              <Descriptions.Item label="Организация">{register.organization?.name ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="Валюта">{register.currency?.code ?? register.currency?.name ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="Сумма">{money(register.total_amount)}</Descriptions.Item>
              <Descriptions.Item label="Строк">{register.rows_count}</Descriptions.Item>
              <Descriptions.Item label="Успешно отправлено">{register.sent_rows_count}</Descriptions.Item>
              <Descriptions.Item label="Ошибок">{register.failed_rows_count}</Descriptions.Item>
              <Descriptions.Item label="Комментарий" span={2}>{register.comment ?? "-"}</Descriptions.Item>
            </Descriptions>

            {canEditHeader ? (
              <Card type="inner" title="Редактирование шапки">
                <Form
                  form={editForm}
                  layout="vertical"
                  initialValues={{
                    number: register.number,
                    date: dayjs(register.date),
                    organization_id: register.organization?.id,
                    currency_id: register.currency?.id,
                    comment: register.comment,
                  }}
                >
                  <Form.Item name="number" label="Номер"><Input /></Form.Item>
                  <Form.Item name="date" label="Дата"><DatePicker style={{ width: "100%" }} /></Form.Item>
                  <Form.Item name="organization_id" label="Организация">
                    <Select allowClear showSearch options={dictionaryOptions(organizationsQuery.data)} optionFilterProp="label" />
                  </Form.Item>
                  <Form.Item name="currency_id" label="Валюта">
                    <Select allowClear showSearch options={dictionaryOptions(currenciesQuery.data)} optionFilterProp="label" />
                  </Form.Item>
                  <Form.Item name="comment" label="Комментарий"><Input.TextArea rows={3} /></Form.Item>
                  <Button type="primary" onClick={() => void submitHeaderUpdate()} loading={updateMutation.isPending}>Сохранить</Button>
                </Form>
              </Card>
            ) : null}
          </Space>
        ) : null}
      </Card>

      <Card title="Строки реестра">
        <Table<PaymentRegisterRow> rowKey="id" dataSource={register?.rows ?? []} columns={rowColumns} pagination={false} />
      </Card>

      <Modal
        open={addModalOpen}
        title="Добавить заявки на оплату"
        width={1100}
        onCancel={() => { setAddModalOpen(false); setSelection([]); }}
        onOk={() => addRowsMutation.mutate(selection)}
        confirmLoading={addRowsMutation.isPending}
        okButtonProps={{ disabled: selection.length === 0 }}
        okText="Добавить"
        cancelText="Отмена"
      >
        <Space direction="vertical" style={{ width: "100%" }} size={12}>
          <Input.Search placeholder="Поиск по номеру или заголовку" allowClear onSearch={setAvailableSearch} />
          <Checkbox checked={includeFailed} onChange={(event) => setIncludeFailed(event.target.checked)}>Показывать заявки с неуспешной историей экспорта</Checkbox>
          {availableQuery.isError ? <Alert type="error" showIcon message={apiError(availableQuery.error, "Не удалось загрузить доступные заявки")} /> : null}
          <Table<AvailablePaymentRequest>
            rowKey="document_id"
            loading={availableQuery.isLoading}
            dataSource={availableQuery.data?.items ?? []}
            rowSelection={{ selectedRowKeys: selection, onChange: (keys) => setSelection(keys.map(String)) }}
            columns={availableColumns}
            pagination={false}
            size="small"
          />
        </Space>
      </Modal>
    </Space>
  );
};
