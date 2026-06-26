import { EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Card, Checkbox, Form, Input, Modal, Select, Space, Table, Tag, Typography, message } from "antd";
import { useMemo, useState } from "react";

import {
  addRolePermission,
  addUserRole,
  createRole,
  getPermissions,
  getRoles,
  getUserRoles,
  removeRolePermission,
  removeUserRole,
  updateRole,
} from "../../entities/role";
import type { PermissionItem, RoleItem, RolePayload } from "../../entities/role";
import { getUsers } from "../../entities/user";
import type { UserItem } from "../../entities/user";
import { Can } from "../../shared/auth/Can";

const apiError = (error: unknown, fallback: string) =>
  (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error?.message ??
  (error as Error)?.message ??
  fallback;

export const RolesPermissionsPage = () => {
  const [form] = Form.useForm<RolePayload>();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleItem | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: getRoles });
  const permissionsQuery = useQuery({ queryKey: ["permissions"], queryFn: getPermissions });
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: getUsers });
  const userRolesQuery = useQuery({
    queryKey: ["user-roles", selectedUserId],
    queryFn: () => getUserRoles(selectedUserId as string),
    enabled: Boolean(selectedUserId),
  });

  const selectedRole = useMemo(
    () => rolesQuery.data?.find((role) => role.id === selectedRoleId) ?? rolesQuery.data?.[0] ?? null,
    [rolesQuery.data, selectedRoleId],
  );

  const closeModal = () => {
    setOpen(false);
    setEditingRole(null);
    form.resetFields();
  };

  const refreshRoles = async () => {
    await Promise.all([queryClient.invalidateQueries({ queryKey: ["roles"] }), queryClient.invalidateQueries({ queryKey: ["user-roles"] })]);
  };

  const saveRoleMutation = useMutation({
    mutationFn: (payload: RolePayload) => (editingRole ? updateRole(editingRole.id, payload) : createRole(payload)),
    onSuccess: async () => {
      message.success(editingRole ? "Роль обновлена" : "Роль создана");
      closeModal();
      await refreshRoles();
    },
    onError: (error) => message.error(apiError(error, "Ошибка сохранения роли")),
  });

  const permissionMutation = useMutation({
    mutationFn: ({ permission, checked }: { permission: PermissionItem; checked: boolean }) => {
      if (!selectedRole) throw new Error("Role is not selected");
      return checked ? addRolePermission(selectedRole.id, permission.id) : removeRolePermission(selectedRole.id, permission.id);
    },
    onSuccess: () => void refreshRoles(),
    onError: (error) => message.error(apiError(error, "Ошибка изменения прав роли")),
  });

  const userRoleMutation = useMutation({
    mutationFn: ({ roleId, checked }: { roleId: string; checked: boolean }) => {
      if (!selectedUserId) throw new Error("User is not selected");
      return checked ? addUserRole(selectedUserId, roleId) : removeUserRole(selectedUserId, roleId);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["user-roles", selectedUserId] });
    },
    onError: (error) => message.error(apiError(error, "Ошибка изменения ролей пользователя")),
  });

  const openCreate = () => {
    setEditingRole(null);
    form.setFieldsValue({ code: "", name: "", description: "", is_active: true });
    setOpen(true);
  };

  const openEdit = (role: RoleItem) => {
    setEditingRole(role);
    form.setFieldsValue({ code: role.code, name: role.name, description: role.description ?? "", is_active: role.is_active });
    setOpen(true);
  };

  const selectedRolePermissions = new Set(selectedRole?.permissions.map((permission) => permission.id) ?? []);
  const selectedUserRoleIds = new Set(userRolesQuery.data?.map((role) => role.id) ?? []);

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      {rolesQuery.isError ? <Alert type="error" showIcon message={apiError(rolesQuery.error, "Ошибка загрузки ролей")} /> : null}
      <Card>
        <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            Роли и права
          </Typography.Title>
          <Can permission="role.create">
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              Создать роль
            </Button>
          </Can>
        </Space>
        <Table<RoleItem>
          rowKey="id"
          loading={rolesQuery.isLoading}
          dataSource={rolesQuery.data ?? []}
          onRow={(role) => ({ onClick: () => setSelectedRoleId(role.id) })}
          rowClassName={(role) => (role.id === selectedRole?.id ? "ant-table-row-selected" : "")}
          columns={[
            { title: "Код", dataIndex: "code" },
            { title: "Название", dataIndex: "name" },
            { title: "Активна", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "red"}>{value ? "Да" : "Нет"}</Tag> },
            {
              title: "Права",
              render: (_, role) => <Tag>{role.permissions.length}</Tag>,
            },
            {
              title: "Действия",
              render: (_, role) => (
                <Can permission="role.update">
                  <Button icon={<EditOutlined />} onClick={() => openEdit(role)}>
                    Изменить
                  </Button>
                </Can>
              ),
            },
          ]}
        />
      </Card>

      <Card title={selectedRole ? `Права роли: ${selectedRole.name}` : "Права роли"}>
        <Space wrap>
          {(permissionsQuery.data ?? []).map((permission) => (
            <Checkbox
              key={permission.id}
              checked={selectedRolePermissions.has(permission.id)}
              disabled={!selectedRole || permissionMutation.isPending}
              onChange={(event) => permissionMutation.mutate({ permission, checked: event.target.checked })}
            >
              {permission.code}
            </Checkbox>
          ))}
        </Space>
      </Card>

      <Card title="Роли пользователя">
        <Space direction="vertical" style={{ width: "100%" }}>
          <Select
            showSearch
            placeholder="Выберите пользователя"
            value={selectedUserId}
            onChange={setSelectedUserId}
            optionFilterProp="label"
            options={(usersQuery.data ?? []).map((user: UserItem) => ({ value: user.id, label: `${user.full_name} <${user.email}>` }))}
          />
          <Space wrap>
            {(rolesQuery.data ?? []).map((role) => (
              <Checkbox
                key={role.id}
                checked={selectedUserRoleIds.has(role.id)}
                disabled={!selectedUserId || userRoleMutation.isPending}
                onChange={(event) => userRoleMutation.mutate({ roleId: role.id, checked: event.target.checked })}
              >
                {role.name}
              </Checkbox>
            ))}
          </Space>
        </Space>
      </Card>

      <Modal title={editingRole ? "Изменить роль" : "Создать роль"} open={open} onCancel={closeModal} footer={null}>
        <Form form={form} layout="vertical" onFinish={(values) => saveRoleMutation.mutate(values)} initialValues={{ is_active: true }}>
          <Form.Item name="code" label="Код" rules={[{ required: true }]}>
            <Input disabled={Boolean(editingRole)} />
          </Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="is_active" valuePropName="checked">
            <Checkbox>Активна</Checkbox>
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={saveRoleMutation.isPending}>
            Сохранить
          </Button>
        </Form>
      </Modal>
    </Space>
  );
};
