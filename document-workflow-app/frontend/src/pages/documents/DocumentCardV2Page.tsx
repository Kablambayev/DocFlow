import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Card, Collapse, Descriptions, Form, Input, Modal, Space, Tabs, Tag, Typography, message } from "antd";
import { useEffect } from "react";
import { useParams } from "react-router-dom";

import { getDocument, submitDocument, updateDocument, withdrawDocument } from "../../entities/document";
import { getDocumentType, getDocumentTypeVersion } from "../../entities/document-type";
import { getPaymentRequest1CExport, sendPaymentRequestTo1C } from "../../entities/integration1c";
import type { PaymentRequest1CExport, PaymentRequest1CSendResult } from "../../entities/integration1c";
import { setUserIdHeader } from "../../shared/api/axios";
import { Can } from "../../shared/auth/Can";
import { useAuth } from "../../shared/auth/useAuth";
import { ApprovalTimelinePanel } from "../../shared/ui/ApprovalTimelinePanel";
import { CommentsPanel } from "../../shared/ui/CommentsPanel";
import { DocumentFilesPanel } from "../../shared/ui/DocumentFilesPanel";
import { DocumentHistoryPanel } from "../../shared/ui/DocumentHistoryPanel";
import { DynamicFormRenderer } from "../../shared/ui/DynamicFormRenderer";
import { normalizeDynamicInitialValues } from "../../shared/ui/dynamicForm";

const editableStatuses = ["Draft", "Withdrawn"];
const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

export const DocumentCardV2Page = () => {
  const { id } = useParams();
  const [form] = Form.useForm();
  const [modal, modalContextHolder] = Modal.useModal();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const documentQuery = useQuery({ queryKey: ["document", id], queryFn: () => getDocument(id ?? ""), enabled: Boolean(id) });
  const versionQuery = useQuery({
    queryKey: ["document-type-version", documentQuery.data?.document_type_version_id],
    queryFn: () => getDocumentTypeVersion(documentQuery.data?.document_type_version_id ?? ""),
    enabled: Boolean(documentQuery.data?.document_type_version_id),
  });
  const documentTypeQuery = useQuery({
    queryKey: ["document-type", documentQuery.data?.document_type_id],
    queryFn: () => getDocumentType(documentQuery.data?.document_type_id ?? ""),
    enabled: Boolean(documentQuery.data?.document_type_id),
  });
  const document = documentQuery.data;
  const schema = versionQuery.data?.schema_json;
  const canEdit = document ? editableStatuses.includes(document.approval_status) : false;
  const canWithdraw = document?.approval_status === "OnApproval";
  const canSendTo1C = hasPermission("integration_1c.payment_request.send");
  const isKnownPaymentRequest = documentTypeQuery.data?.code === "PaymentRequest";

  const exportQuery = useQuery({
    queryKey: ["document-1c-export", id],
    queryFn: () => getPaymentRequest1CExport(id ?? ""),
    enabled: Boolean(id) && (isKnownPaymentRequest || canSendTo1C),
  });
  const isPaymentRequest = isKnownPaymentRequest || (canSendTo1C && exportQuery.isSuccess);

  useEffect(() => {
    if (document && schema) {
      form.setFieldsValue({ current_user_id: localStorage.getItem("docflow_user_id") ?? "", title: document.title, ...normalizeDynamicInitialValues(document.data_json, schema) });
    }
  }, [document, form, schema]);

  const updateMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const data_json: Record<string, unknown> = {};
      for (const section of schema?.sections ?? []) {
        for (const field of section.fields) data_json[field.code] = values[field.code];
      }
      return updateDocument(id ?? "", { title: String(values.title ?? document?.title ?? ""), data_json });
    },
    onSuccess: () => {
      message.success("Документ обновлен");
      void documentQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления")),
  });

  const submitMutation = useMutation({
    mutationFn: () => submitDocument(id ?? ""),
    onSuccess: () => {
      message.success("Документ отправлен на согласование");
      void documentQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка отправки")),
  });

  const withdrawMutation = useMutation({
    mutationFn: () => withdrawDocument(id ?? ""),
    onSuccess: () => {
      message.success("Документ отозван");
      void documentQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка отзыва")),
  });

  const refresh1CState = async () => {
    await Promise.all([
      documentQuery.refetch(),
      exportQuery.refetch(),
      queryClient.invalidateQueries({ queryKey: ["document-timeline", id] }),
      queryClient.invalidateQueries({ queryKey: ["notifications", "my"] }),
      queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count"] }),
    ]);
  };

  const sendTo1CMutation = useMutation({
    mutationFn: ({ force }: { force: boolean }) => sendPaymentRequestTo1C(id ?? "", force),
    onSuccess: async (result: PaymentRequest1CSendResult) => {
      if (result.status === "already_exported") {
        message.info("Заявка уже была отправлена в 1С");
      } else if (result.status === "Failed") {
        message.error(result.error?.message ?? "Ошибка отправки заявки в 1С");
      } else {
        message.success(result.one_c_enabled === false ? "Отправлено в fake 1С" : "Заявка отправлена в 1С");
      }
      await refresh1CState();
    },
    onError: (error) => message.error(apiError(error, "Ошибка отправки в 1С")),
  });

  const onFinish = (values: Record<string, unknown>) => {
    setUserIdHeader(values.current_user_id ? String(values.current_user_id) : null);
    updateMutation.mutate(values);
  };

  const triggerSendTo1C = (force: boolean) => {
    if (force) {
      modal.confirm({
        title: "Повторить отправку в 1С?",
        content: "Будет выполнена принудительная повторная отправка с force=true.",
        okText: "Повторить",
        cancelText: "Отмена",
        onOk: async () => {
          await sendTo1CMutation.mutateAsync({ force: true });
        },
      });
      return;
    }
    sendTo1CMutation.mutate({ force: false });
  };

  const render1CTab = () => {
    const currentDocument = document!;
    const exportState = exportQuery.data;
    const exportData = exportState && exportState.status !== "not_exported" ? (exportState as PaymentRequest1CExport) : null;
    const isApproved = currentDocument.approval_status === "Approved";
    const showRepeat = canSendTo1C && ["CreatedIn1C", "AlreadyExistsIn1C", "Failed"].includes(exportData?.status ?? "");

    return (
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        {exportQuery.isError ? <Alert type="error" showIcon message={apiError(exportQuery.error, "Ошибка загрузки статуса 1С")} /> : null}
        {!isApproved ? <Alert type="info" showIcon message="Отправка в 1С доступна после полного согласования заявки." /> : null}
        {isApproved && exportState?.status === "not_exported" ? (
          <Card>
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Typography.Text>Экспорт в 1С еще не выполнялся.</Typography.Text>
              {canSendTo1C ? (
                <Button type="primary" loading={sendTo1CMutation.isPending} onClick={() => triggerSendTo1C(false)}>
                  Отправить в 1С
                </Button>
              ) : (
                <Typography.Text type="secondary">У вас нет прав на ручную отправку в 1С.</Typography.Text>
              )}
            </Space>
          </Card>
        ) : null}
        {exportData && ["CreatedIn1C", "AlreadyExistsIn1C"].includes(exportData.status) ? (
          <Card>
            <Descriptions bordered column={1}>
              <Descriptions.Item label="Статус">
                <Tag color={exportData.status === "CreatedIn1C" ? "green" : "blue"}>
                  {exportData.status === "CreatedIn1C" ? "Создано в 1С" : "Уже существовало в 1С"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Номер платежного поручения">{exportData.one_c_payment_order_number ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="Дата">{exportData.one_c_payment_order_date ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="Сумма">{exportData.one_c_payment_order_amount ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="Валюта">{exportData.one_c_payment_order_currency_code ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="External ID 1С">{exportData.one_c_payment_order_external_id ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="Отправлено">{exportData.sent_at ?? "-"}</Descriptions.Item>
            </Descriptions>
            {showRepeat ? (
              <Button style={{ marginTop: 16 }} loading={sendTo1CMutation.isPending} onClick={() => triggerSendTo1C(true)}>
                Повторить отправку
              </Button>
            ) : null}
          </Card>
        ) : null}
        {exportData?.status === "Failed" ? (
          <Card>
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Alert type="error" showIcon message="Ошибка отправки" description={exportData.error_message ?? "Неизвестная ошибка"} />
              <Descriptions bordered column={1}>
                <Descriptions.Item label="Код ошибки">{exportData.error_code ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="Сообщение">{exportData.error_message ?? "-"}</Descriptions.Item>
              </Descriptions>
              {canSendTo1C ? (
                <Button loading={sendTo1CMutation.isPending} onClick={() => triggerSendTo1C(true)}>
                  Повторить отправку
                </Button>
              ) : null}
            </Space>
          </Card>
        ) : null}
      </Space>
    );
  };

  if (documentQuery.isLoading || !document) return <Card loading />;

  const tabItems = [
    {
      key: "main",
      label: "Основное",
      children: (
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="current_user_id" label="Current User ID (X-User-Id)"><Input placeholder="uuid" /></Form.Item>
          <Form.Item name="title" label="Заголовок" rules={[{ required: true }]}><Input disabled={!canEdit} /></Form.Item>
          {schema ? (
            <DynamicFormRenderer
              schema={schema}
              disabled={!canEdit}
              documentId={document.id}
              documentStatus={document.approval_status}
            />
          ) : <Alert type="info" showIcon message="Схема формы не загружена." />}
          <Space>
            {canEdit ? <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>Сохранить</Button> : null}
            {canEdit ? <Button type="primary" loading={submitMutation.isPending} onClick={() => submitMutation.mutate()}>Отправить на согласование</Button> : null}
            {canWithdraw ? <Button danger loading={withdrawMutation.isPending} onClick={() => withdrawMutation.mutate()}>Отозвать</Button> : null}
            <Button onClick={() => void documentQuery.refetch()}>Обновить</Button>
          </Space>
          <Collapse style={{ marginTop: 16 }} items={[{ key: "debug", label: "Raw data_json", children: <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(document.data_json, null, 2)}</pre> }]} />
        </Form>
      ),
    },
    {
      key: "files",
      label: "Файлы",
      children: (
        <Can permission="document_file.read">
          <DocumentFilesPanel documentId={document.id} documentStatus={document.approval_status} />
        </Can>
      ),
    },
    {
      key: "comments",
      label: "Комментарии",
      children: <CommentsPanel documentId={document.id} />,
    },
    {
      key: "approval",
      label: "Согласование",
      children: <ApprovalTimelinePanel documentId={document.id} />,
    },
    {
      key: "history",
      label: "История",
      children: <DocumentHistoryPanel documentId={document.id} />,
    },
  ];

  if (isPaymentRequest) {
    tabItems.splice(4, 0, { key: "one_c", label: "1С", children: render1CTab() });
  }

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {modalContextHolder}
      {documentQuery.isError ? <Alert type="error" showIcon message={apiError(documentQuery.error, "Ошибка загрузки документа")} /> : null}
      <Card title={`Документ ${document.number}`}>
        <Descriptions bordered column={1}>
          <Descriptions.Item label="Номер">{document.number}</Descriptions.Item>
          <Descriptions.Item label="Заголовок">{document.title}</Descriptions.Item>
          <Descriptions.Item label="Статус"><Tag>{document.approval_status}</Tag></Descriptions.Item>
          <Descriptions.Item label="Автор">{document.author_id}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card>
        <Tabs items={tabItems} />
      </Card>
    </Space>
  );
};
