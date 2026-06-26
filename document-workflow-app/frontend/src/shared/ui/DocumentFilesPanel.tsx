import { DeleteOutlined, DownloadOutlined, FileOutlined, InboxOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Empty, List, Modal, Space, Tag, Typography, Upload, message } from "antd";

import { deleteFile, downloadFileBlob, getDocumentFiles, uploadDocumentFile } from "../../entities/file";
import type { DocumentFile } from "../../entities/file";
import { useAuth } from "../auth/useAuth";

const editableStatuses = ["Draft", "Withdrawn"];

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const saveBlob = (file: DocumentFile, blob: Blob) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.file_name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

interface DocumentFilesPanelProps {
  documentId: string;
  documentStatus: string;
  readonly?: boolean;
  fieldCode?: string;
}

export const DocumentFilesPanel = ({ documentId, documentStatus, readonly, fieldCode }: DocumentFilesPanelProps) => {
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canRead = hasPermission("document_file.read");
  const canUpload = hasPermission("document_file.upload") && editableStatuses.includes(documentStatus) && !readonly;
  const canDelete = hasPermission("document_file.delete") && editableStatuses.includes(documentStatus) && !readonly;

  const filesQuery = useQuery({
    queryKey: ["document-files", documentId],
    queryFn: () => getDocumentFiles(documentId),
    enabled: Boolean(documentId) && canRead,
  });

  const visibleFiles = (filesQuery.data ?? []).filter((item) => !fieldCode || item.field_code === fieldCode);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocumentFile(documentId, file, fieldCode),
    onSuccess: async () => {
      message.success("Файл прикреплен");
      await queryClient.invalidateQueries({ queryKey: ["document-files", documentId] });
    },
    onError: (error) => message.error(apiError(error, "Ошибка загрузки файла")),
  });

  const downloadMutation = useMutation({
    mutationFn: async (file: DocumentFile) => ({ file, blob: await downloadFileBlob(file.id) }),
    onSuccess: ({ file, blob }) => saveBlob(file, blob),
    onError: (error) => message.error(apiError(error, "Ошибка скачивания файла")),
  });

  const deleteMutation = useMutation({
    mutationFn: (file: DocumentFile) => deleteFile(file.id),
    onSuccess: async () => {
      message.success("Файл удален");
      await queryClient.invalidateQueries({ queryKey: ["document-files", documentId] });
    },
    onError: (error) => message.error(apiError(error, "Ошибка удаления файла")),
  });

  if (!canRead) {
    return <Alert type="warning" showIcon message="Недостаточно прав для просмотра файлов" />;
  }

  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      {filesQuery.isError ? <Alert type="error" showIcon message={apiError(filesQuery.error, "Ошибка загрузки файлов")} /> : null}
      {canUpload ? (
        <Upload.Dragger
          multiple
          showUploadList={false}
          disabled={uploadMutation.isPending}
          beforeUpload={(file) => {
            uploadMutation.mutate(file);
            return false;
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <Typography.Text>Перетащите файлы сюда или нажмите для выбора</Typography.Text>
        </Upload.Dragger>
      ) : null}

      {visibleFiles.length === 0 && !filesQuery.isLoading ? <Empty description="Файлы не прикреплены" /> : null}

      <List
        loading={filesQuery.isLoading}
        dataSource={visibleFiles}
        renderItem={(file) => (
          <List.Item
            actions={[
              <Button
                key="download"
                icon={<DownloadOutlined />}
                onClick={() => downloadMutation.mutate(file)}
                loading={downloadMutation.isPending}
              />,
              canDelete ? (
                <Button
                  key="delete"
                  danger
                  icon={<DeleteOutlined />}
                  loading={deleteMutation.isPending}
                  onClick={() =>
                    Modal.confirm({
                      title: "Удалить файл?",
                      content: file.file_name,
                      okText: "Удалить",
                      okButtonProps: { danger: true },
                      cancelText: "Отмена",
                      onOk: () => deleteMutation.mutate(file),
                    })
                  }
                />
              ) : null,
            ].filter(Boolean)}
          >
            <List.Item.Meta
              avatar={<FileOutlined style={{ fontSize: 22 }} />}
              title={file.file_name}
              description={
                <Space wrap>
                  <Tag>{formatSize(file.size_bytes)}</Tag>
                  <Typography.Text type="secondary">{file.content_type}</Typography.Text>
                  {file.field_code ? <Tag color="blue">{file.field_code}</Tag> : null}
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </Space>
  );
};
