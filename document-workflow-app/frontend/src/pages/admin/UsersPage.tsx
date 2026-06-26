import { CopyOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Checkbox, Form, Input, Modal, Space, Table, Tag, Typography, message } from "antd";
import { useState } from "react";

import { createUser, getUsers, updateUser } from "../../entities/user";
import type { UserItem, UserPayload } from "../../entities/user";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

export const UsersPage = () => {
  const [form] = Form.useForm<UserPayload>();
  const [open, setOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: getUsers });

  const closeModal = () => {
    setOpen(false);
    setEditingUser(null);
    form.resetFields();
  };

  const saveMutation = useMutation({
    mutationFn: (payload: UserPayload) => (editingUser ? updateUser(editingUser.id, payload) : createUser(payload)),
    onSuccess: () => {
      message.success(editingUser ? "Пользователь обновлен" : "Пользователь создан");
      closeModal();
      void usersQuery.refetch();
    },
    onError: (error) => message.error(apiError(error, "Ошибка сохранения пользователя")),
  });

  const openCreate = () => {
    setEditingUser(null);
    form.setFieldsValue({ email: "", full_name: "", is_active: true });
    setOpen(true);
  };

  const openEdit = (user: UserItem) => {
    setEditingUser(user);
    form.setFieldsValue({ email: user.email, full_name: user.full_name, is_active: user.is_active });
    setOpen(true);
  };

  const copyId = async (id: string) => {
    await navigator.clipboard.writeText(id);
    message.success("ID скопирован");
  };

  return (
    <Card>
      {usersQuery.isError ? <Alert type="error" showIcon message={apiError(usersQuery.error, "Ошибка загрузки пользователей")} style={{ marginBottom: 16 }} /> : null}
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Пользователи
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Создать пользователя
        </Button>
      </Space>
      <Table<UserItem>
        rowKey="id"
        loading={usersQuery.isLoading}
        dataSource={usersQuery.data ?? []}
        columns={[
          { title: "Email", dataIndex: "email" },
          { title: "ФИО", dataIndex: "full_name" },
          { title: "Активен", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Да" : "Нет"}</Tag> },
          {
            title: "ID",
            dataIndex: "id",
            render: (id: string) => (
              <Space>
                <Typography.Text code copyable={false}>{id}</Typography.Text>
                <Button icon={<CopyOutlined />} onClick={() => void copyId(id)} />
              </Space>
            ),
          },
          {
            title: "Действия",
            render: (_, user) => (
              <Button icon={<EditOutlined />} onClick={() => openEdit(user)}>
                Редактировать
              </Button>
            ),
          },
        ]}
      />

      <Modal title={editingUser ? "Редактировать пользователя" : "Создать пользователя"} open={open} onCancel={closeModal} footer={null}>
        <Form form={form} layout="vertical" onFinish={(values) => saveMutation.mutate(values)} initialValues={{ is_active: true }}>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: "email" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="full_name" label="ФИО" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="is_active" valuePropName="checked">
            <Checkbox>Активен</Checkbox>
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={saveMutation.isPending}>
            Сохранить
          </Button>
        </Form>
      </Modal>
    </Card>
  );
};
