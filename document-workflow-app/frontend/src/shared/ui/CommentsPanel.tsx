import { DeleteOutlined, EditOutlined, SaveOutlined, CloseOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Empty, Input, List, Modal, Space, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { useState } from "react";

import { createDocumentComment, deleteDocumentComment, getDocumentComments, updateDocumentComment } from "../../entities/comment";
import type { DocumentComment } from "../../entities/comment";
import { useAuth } from "../auth/useAuth";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

const commentTypeColor: Record<string, string> = {
  general: "blue",
  approval: "green",
  system: "default",
};

const commentTypeLabel: Record<string, string> = {
  general: "Комментарий",
  approval: "Согласование",
  system: "Система",
};

interface CommentsPanelProps {
  documentId: string;
}

export const CommentsPanel = ({ documentId }: CommentsPanelProps) => {
  const queryClient = useQueryClient();
  const { currentUserId, hasPermission, isAdmin } = useAuth();
  const [commentText, setCommentText] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const canRead = hasPermission("document_comment.read");
  const canCreate = hasPermission("document_comment.create");
  const canUpdate = hasPermission("document_comment.update");
  const canDelete = hasPermission("document_comment.delete");

  const commentsQuery = useQuery({
    queryKey: ["document-comments", documentId],
    queryFn: () => getDocumentComments(documentId),
    enabled: Boolean(documentId) && canRead,
  });

  const createMutation = useMutation({
    mutationFn: () => createDocumentComment(documentId, { comment_text: commentText }),
    onSuccess: async () => {
      setCommentText("");
      message.success("Комментарий добавлен");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["document-comments", documentId] }),
        queryClient.invalidateQueries({ queryKey: ["document-timeline", documentId] }),
      ]);
    },
    onError: (error) => message.error(apiError(error, "Ошибка добавления комментария")),
  });

  const updateMutation = useMutation({
    mutationFn: (comment: DocumentComment) => updateDocumentComment(comment.id, { comment_text: editingText }),
    onSuccess: async () => {
      setEditingId(null);
      setEditingText("");
      message.success("Комментарий обновлен");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["document-comments", documentId] }),
        queryClient.invalidateQueries({ queryKey: ["document-timeline", documentId] }),
      ]);
    },
    onError: (error) => message.error(apiError(error, "Ошибка обновления комментария")),
  });

  const deleteMutation = useMutation({
    mutationFn: (comment: DocumentComment) => deleteDocumentComment(comment.id),
    onSuccess: async () => {
      message.success("Комментарий удален");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["document-comments", documentId] }),
        queryClient.invalidateQueries({ queryKey: ["document-timeline", documentId] }),
      ]);
    },
    onError: (error) => message.error(apiError(error, "Ошибка удаления комментария")),
  });

  const startEdit = (comment: DocumentComment) => {
    setEditingId(comment.id);
    setEditingText(comment.comment_text);
  };

  const isEditable = (comment: DocumentComment) =>
    comment.comment_type === "general" && (comment.author_id === currentUserId || isAdmin);

  if (!canRead) {
    return <Alert type="warning" showIcon message="Недостаточно прав для просмотра комментариев" />;
  }

  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      {commentsQuery.isError ? <Alert type="error" showIcon message={apiError(commentsQuery.error, "Ошибка загрузки комментариев")} /> : null}
      {canCreate ? (
        <Space.Compact style={{ width: "100%" }}>
          <Input.TextArea
            value={commentText}
            autoSize={{ minRows: 2, maxRows: 5 }}
            placeholder="Комментарий"
            onChange={(event) => setCommentText(event.target.value)}
          />
          <Button
            type="primary"
            loading={createMutation.isPending}
            onClick={() => {
              if (!commentText.trim()) {
                message.warning("Введите комментарий");
                return;
              }
              createMutation.mutate();
            }}
          >
            Добавить
          </Button>
        </Space.Compact>
      ) : null}

      {commentsQuery.data?.length === 0 && !commentsQuery.isLoading ? <Empty description="Комментариев пока нет" /> : null}
      <List
        loading={commentsQuery.isLoading}
        dataSource={commentsQuery.data ?? []}
        renderItem={(comment) => (
          <List.Item
            actions={[
              isEditable(comment) && canUpdate ? (
                <Button key="edit" icon={<EditOutlined />} onClick={() => startEdit(comment)} />
              ) : null,
              isEditable(comment) && canDelete ? (
                <Button
                  key="delete"
                  danger
                  icon={<DeleteOutlined />}
                  loading={deleteMutation.isPending}
                  onClick={() =>
                    Modal.confirm({
                      title: "Удалить комментарий?",
                      okText: "Удалить",
                      okButtonProps: { danger: true },
                      cancelText: "Отмена",
                      onOk: () => deleteMutation.mutateAsync(comment),
                    })
                  }
                />
              ) : null,
            ].filter(Boolean)}
          >
            <List.Item.Meta
              title={
                <Space wrap>
                  <Typography.Text strong>{comment.author_name ?? comment.author_id}</Typography.Text>
                  <Tag color={commentTypeColor[comment.comment_type]}>{commentTypeLabel[comment.comment_type] ?? comment.comment_type}</Tag>
                  <Typography.Text type="secondary">{dayjs(comment.created_at).format("DD.MM.YYYY HH:mm")}</Typography.Text>
                </Space>
              }
              description={
                editingId === comment.id ? (
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Input.TextArea value={editingText} autoSize={{ minRows: 2, maxRows: 5 }} onChange={(event) => setEditingText(event.target.value)} />
                    <Space>
                      <Button
                        type="primary"
                        icon={<SaveOutlined />}
                        loading={updateMutation.isPending}
                        onClick={() => {
                          if (!editingText.trim()) {
                            message.warning("Введите комментарий");
                            return;
                          }
                          updateMutation.mutate(comment);
                        }}
                      >
                        Сохранить
                      </Button>
                      <Button icon={<CloseOutlined />} onClick={() => setEditingId(null)}>
                        Отмена
                      </Button>
                    </Space>
                  </Space>
                ) : (
                  <Typography.Paragraph style={{ marginBottom: 0, whiteSpace: "pre-wrap" }}>{comment.comment_text}</Typography.Paragraph>
                )
              }
            />
          </List.Item>
        )}
      />
    </Space>
  );
};
