import { ApiOutlined, CheckCircleOutlined, CloseCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, Descriptions, Row, Space, Spin, Tag, Typography, message } from "antd";
import { Link } from "react-router-dom";

import { getOneCDiagnosticsSettings, testOneCConnection } from "../../entities/integration1c";
import type { OneCTestConnectionResult } from "../../entities/integration1c";
import { Can } from "../../shared/auth/Can";

const apiError = (error: unknown) =>
  (error as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ??
  (error as Error)?.message ?? "Не удалось выполнить запрос";

const flag = (value: boolean) => <Tag color={value ? "green" : "default"}>{value ? "Да" : "Нет"}</Tag>;

const ResultPanel = ({ result }: { result: OneCTestConnectionResult }) => {
  const meta = {
    ok: { type: "success" as const, icon: <CheckCircleOutlined />, title: "Подключение успешно" },
    disabled: { type: "info" as const, icon: <ApiOutlined />, title: "Интеграция с 1С отключена" },
    warning: { type: "warning" as const, icon: <WarningOutlined />, title: "Подключение выполнено, но ответ нестандартный" },
    error: { type: "error" as const, icon: <CloseCircleOutlined />, title: "Ошибка подключения к 1С" },
  }[result.status];
  return <Alert showIcon type={meta.type} icon={meta.icon} message={meta.title} description={
    <Descriptions size="small" column={{ xs: 1, md: 2 }} style={{ marginTop: 12 }}>
      {result.message ? <Descriptions.Item label="Сообщение">{result.message}</Descriptions.Item> : null}
      {result.code ? <Descriptions.Item label="Код">{result.code}</Descriptions.Item> : null}
      {result.http_status != null ? <Descriptions.Item label="HTTP">{result.http_status}</Descriptions.Item> : null}
      {result.duration_ms != null ? <Descriptions.Item label="Время">{result.duration_ms} ms</Descriptions.Item> : null}
      {result.service ? <Descriptions.Item label="Сервис">{result.service}</Descriptions.Item> : null}
      {result.version ? <Descriptions.Item label="Версия">{result.version}</Descriptions.Item> : null}
      {result.details ? <Descriptions.Item label="Детали"><pre style={{ margin: 0 }}>{JSON.stringify(result.details, null, 2)}</pre></Descriptions.Item> : null}
    </Descriptions>
  } />;
};

export const OneCDiagnosticsPage = () => {
  const settingsQuery = useQuery({ queryKey: ["one-c-diagnostics-settings"], queryFn: getOneCDiagnosticsSettings });
  const testMutation = useMutation({ mutationFn: testOneCConnection, onError: (error) => message.error(apiError(error)) });
  const settings = settingsQuery.data;
  const cards: Array<[string, React.ReactNode]> = settings ? [
    ["Интеграция включена", flag(settings.one_c_enabled)],
    ["Base URL настроен", flag(settings.base_url_configured)],
    ["Health endpoint", settings.health_endpoint],
    ["Payment endpoint", settings.payment_request_endpoint],
    ["Timeout", `${settings.timeout_seconds} сек.`],
    ["Username настроен", flag(settings.username_configured)],
    ["Password настроен", flag(settings.password_configured)],
    ["Verify SSL", flag(settings.verify_ssl)],
  ] : [];

  return <Space direction="vertical" size={16} style={{ width: "100%" }}>
    <div>
      <Typography.Title level={4} style={{ margin: 0 }}>Диагностика подключения к 1С</Typography.Title>
      <Typography.Text type="secondary">Проверка доступности HTTP-сервиса 1С и текущих настроек интеграции</Typography.Text>
    </div>
    {settingsQuery.isError ? <Alert showIcon type="error" message={apiError(settingsQuery.error)} /> : null}
    {settingsQuery.isLoading ? <Spin /> : null}
    <Row gutter={[16, 16]}>
      {cards.map(([title, value]) => <Col xs={24} sm={12} lg={6} key={title}><Card size="small" title={title}>{value}</Card></Col>)}
      {settings?.base_url_preview ? <Col span={24}><Card size="small" title="Base URL"><Typography.Text copyable>{settings.base_url_preview}</Typography.Text></Card></Col> : null}
    </Row>
    <Space wrap>
      <Can permission="integration_1c.diagnostics.run">
        <Button type="primary" icon={<ApiOutlined />} loading={testMutation.isPending} onClick={() => testMutation.mutate()}>Проверить подключение</Button>
      </Can>
      <Link to="/integration/logs?operation_type=1c_test_connection">Открыть журнал обмена</Link>
    </Space>
    {testMutation.data ? <ResultPanel result={testMutation.data} /> : null}
  </Space>;
};
