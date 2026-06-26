import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, DatePicker, Form, Input, Select, Space, message } from "antd";
import TextArea from "antd/es/input/TextArea";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom";

import { DynamicFormRenderer } from "../../shared/ui/DynamicFormRenderer";
import type { DynamicFormSchema } from "../../shared/types/document";
import { apiClient, setUserIdHeader } from "../../shared/api/axios";

type DocumentTypeItem = { id: string; code: string; name: string };
type DocumentTypeVersionItem = { id: string; version_number: number; status: string; schema_json: DynamicFormSchema };

const fetchDocumentTypes = async (): Promise<DocumentTypeItem[]> => {
  const { data } = await apiClient.get<DocumentTypeItem[]>("/document-types");
  return data;
};

const fetchVersions = async (documentTypeId: string): Promise<DocumentTypeVersionItem[]> => {
  const { data } = await apiClient.get<DocumentTypeVersionItem[]>("/document-type-versions", {
    params: { document_type_id: documentTypeId },
  });
  return data;
};

export const CreateDocumentPage = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const { data: documentTypes = [] } = useQuery({ queryKey: ["document-types"], queryFn: fetchDocumentTypes });

  const selectedDocumentTypeId = Form.useWatch("document_type_id", form);
  const selectedVersionId = Form.useWatch("document_type_version_id", form);

  const { data: versions = [] } = useQuery({
    queryKey: ["document-type-versions", selectedDocumentTypeId],
    queryFn: () => fetchVersions(selectedDocumentTypeId),
    enabled: Boolean(selectedDocumentTypeId),
  });

  const selectedVersion = versions.find((item) => item.id === selectedVersionId);

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await apiClient.post("/documents", payload);
      return data;
    },
    onSuccess: (data) => {
      message.success("Документ создан");
      navigate(`/documents/${data.id}`);
    },
    onError: (error: any) => {
      message.error(error?.response?.data?.error?.message ?? "Ошибка создания документа");
    },
  });

  const onFinish = (values: any) => {
    try {
      setUserIdHeader(values.current_user_id);
      const parsedDataJson = values.data_json ? JSON.parse(values.data_json) : {};
      createMutation.mutate({
        document_type_id: values.document_type_id,
        document_type_version_id: values.document_type_version_id,
        number: values.number,
        document_date: dayjs(values.document_date).toISOString(),
        author_id: values.author_id,
        organization_id: values.organization_id || null,
        department_id: values.department_id || null,
        title: values.title,
        data_json: parsedDataJson,
      });
    } catch {
      message.error("Некорректный JSON в data_json");
    }
  };

  return (
    <Card title="Создание документа">
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="Для workflow API укажи X-User-Id в поле Current User ID"
      />
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item name="current_user_id" label="Current User ID (X-User-Id)">
          <Input placeholder="uuid" />
        </Form.Item>
        <Form.Item name="author_id" label="Author ID" rules={[{ required: true }]}>
          <Input placeholder="uuid" />
        </Form.Item>
        <Form.Item name="document_type_id" label="Document Type" rules={[{ required: true }]}>
          <Select
            options={documentTypes.map((item) => ({ value: item.id, label: `${item.code} - ${item.name}` }))}
            placeholder="Выбери тип документа"
          />
        </Form.Item>
        <Form.Item name="document_type_version_id" label="Document Type Version" rules={[{ required: true }]}>
          <Select
            options={versions.map((item) => ({ value: item.id, label: `v${item.version_number} (${item.status})` }))}
            placeholder="Выбери версию"
          />
        </Form.Item>
        <Form.Item name="number" label="Номер" rules={[{ required: true }]}>
          <Input placeholder="PAY-000001" />
        </Form.Item>
        <Form.Item name="document_date" label="Дата документа" rules={[{ required: true }]}>
          <DatePicker showTime style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="title" label="Заголовок" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="organization_id" label="Organization ID">
          <Input placeholder="uuid или пусто" />
        </Form.Item>
        <Form.Item name="department_id" label="Department ID">
          <Input placeholder="uuid или пусто" />
        </Form.Item>
        <Form.Item name="data_json" label="Data JSON" initialValue="{}">
          <TextArea rows={8} />
        </Form.Item>

        {selectedVersion?.schema_json ? <DynamicFormRenderer schema={selectedVersion.schema_json} /> : null}

        <Space>
          <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
            Сохранить
          </Button>
        </Space>
      </Form>
    </Card>
  );
};
