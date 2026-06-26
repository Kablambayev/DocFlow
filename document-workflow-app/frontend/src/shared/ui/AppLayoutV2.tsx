import { Button, Input, Layout, Menu, Select, Space, Tag, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import type { PropsWithChildren } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { getUsers } from "../../entities/user";
import { useAuth } from "../auth/useAuth";

const { Header, Sider, Content } = Layout;

const menuPermissionsByKey: Record<string, { permission?: string; anyOf?: string[] }> = {
  "/documents": { permission: "document.read" },
  "/tasks": { anyOf: ["task.read", "document.approve"] },
  "/admin": { anyOf: ["admin.access", "document_type.read", "approval_route.read", "approval_matrix.read", "user.read", "role.read", "permission.read"] },
  "/admin/document-types": { permission: "document_type.read" },
  "/admin/routes": { permission: "approval_route.read" },
  "/admin/matrix": { permission: "approval_matrix.read" },
  "/admin/users": { permission: "user.read" },
  "/admin/roles": { anyOf: ["role.read", "permission.read"] },
};

type MenuItem = {
  key: string;
  label: string;
  icon?: React.ReactNode;
  permission?: string;
  anyOf?: string[];
};

interface AppLayoutProps extends PropsWithChildren {
  menuItems: MenuItem[];
}

export const AppLayoutV2 = ({ menuItems }: AppLayoutProps) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentUser, currentUserId, permissions, setCurrentUserId, refreshAuth, hasPermission, hasAnyPermission } = useAuth();
  const usersQuery = useQuery({ queryKey: ["users", "layout"], queryFn: getUsers, enabled: hasPermission("user.read"), retry: false });
  const sourceMenuItems = [...menuItems, { key: "/admin/roles", label: "Роли и права" }];
  const visibleMenuItems = sourceMenuItems
    .filter((item) => {
      const rule = { ...menuPermissionsByKey[item.key], permission: item.permission, anyOf: item.anyOf };
      if (rule.permission) return hasPermission(rule.permission);
      if (rule.anyOf) return hasAnyPermission(rule.anyOf);
      return true;
    })
    .map(({ permission: _permission, anyOf: _anyOf, ...item }) => item);

  return (
    <Layout style={{ minHeight: "100vh", background: "linear-gradient(180deg, #f3f6f7 0%, #e9efee 100%)" }}>
      <Sider width={280} theme="light" style={{ borderRight: "1px solid #d8e2e0" }}>
        <div style={{ padding: 20 }}>
          <Typography.Title level={4} style={{ margin: 0, color: "#0a6e6e" }}>
            DocFlow
          </Typography.Title>
          <Typography.Text type="secondary">ЭДО и согласования</Typography.Text>
        </div>
        <Menu selectedKeys={[location.pathname]} mode="inline" items={visibleMenuItems} onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout>
        <Header style={{ background: "#ffffff", borderBottom: "1px solid #d8e2e0", padding: "12px 20px", height: "auto" }}>
          <Typography.Title level={5} style={{ margin: "16px 0" }}>
            Управление документами
          </Typography.Title>
          {currentUser ? <Typography.Text type="secondary">{currentUser.full_name}</Typography.Text> : null}
          <Space wrap style={{ marginLeft: 16 }}>
            <Select
              allowClear
              showSearch
              placeholder="Dev user"
              value={currentUserId}
              style={{ width: 260 }}
              optionFilterProp="label"
              loading={usersQuery.isLoading}
              onChange={(value) => setCurrentUserId(value ?? null)}
              options={(usersQuery.data ?? []).map((user) => ({ value: user.id, label: `${user.full_name} <${user.email}>` }))}
            />
            <Input
              placeholder="X-User-Id"
              value={currentUserId ?? ""}
              style={{ width: 280 }}
              onChange={(event) => setCurrentUserId(event.target.value || null)}
            />
            <Button onClick={() => void refreshAuth()}>Обновить права</Button>
            <Tag color={permissions.includes("admin.access") ? "green" : "blue"}>{permissions.length} прав</Tag>
          </Space>
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};
