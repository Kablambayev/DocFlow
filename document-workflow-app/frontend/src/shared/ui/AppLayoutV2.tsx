import { Button, Input, Layout, Menu, Select, Space, Tag, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import type { PropsWithChildren } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { getUsers } from "../../entities/user";
import { useAuth } from "../auth/useAuth";
import { NotificationsDropdown } from "./NotificationsDropdown";

const { Header, Sider, Content } = Layout;

const menuPermissionsByKey: Record<string, { permission?: string; anyOf?: string[] }> = {
  "/documents": { permission: "document.read" },
  "/tasks": { anyOf: ["task.read", "document.approve"] },
  "/treasury/payment-requests": { permission: "treasury.payment_request.read" },
  "/payment-registers": { permission: "payment_register.read" },
  "/integration/logs": { permission: "integration.log.read" },
  "/integration/1c/diagnostics": { permission: "integration_1c.diagnostics.read" },
  "/accounting": { permission: "accounting.read" },
  "/cash-flow/mapping-rules": { permission: "cash_flow.mapping.read" },
  "/admin": { anyOf: ["admin.access", "document_type.read", "approval_route.read", "approval_matrix.read", "user.read", "role.read", "permission.read"] },
  "/admin/document-types": { permission: "document_type.read" },
  "/admin/routes": { permission: "approval_route.read" },
  "/admin/matrix": { permission: "approval_matrix.read" },
  "/admin/users": { permission: "user.read" },
  "/admin/roles": { anyOf: ["role.read", "permission.read"] },
};

const devUserOptions = [
  { value: "ac9d2376-34a0-439f-b8fc-319418b9fb57", label: "Admin User <admin@example.com>" },
  { value: "ec42a60c-3ce6-42ca-892f-c8ac286d472f", label: "Author User <author@example.com>" },
  { value: "430fe9f5-f037-41fc-815e-abcf24e62eb5", label: "Approver User <approver@example.com>" },
  { value: "db277dc4-ecd2-471d-8529-88fb698ecf0d", label: "Accounting Admin <accounting_admin@example.com>" },
  { value: "08c40803-c674-483c-b70a-09224b824310", label: "Technical Admin <technical_admin@example.com>" },
];

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
  const { currentUser, currentUserId, permissions, isLoading, setCurrentUserId, refreshAuth, hasPermission, hasAnyPermission } = useAuth();
  const usersQuery = useQuery({ queryKey: ["users", "layout"], queryFn: getUsers, enabled: hasPermission("user.read"), retry: false });
  const sourceMenuItems = [
    ...menuItems,
    { key: "/integration/logs", label: "Журнал обмена" },
    { key: "/admin/roles", label: "Роли и права" },
  ];
  const visibleMenuItems = sourceMenuItems
    .filter((item) => {
      if (!currentUserId || isLoading) return true;
      const configuredRule = menuPermissionsByKey[item.key];
      const rule = {
        permission: item.permission ?? configuredRule?.permission,
        anyOf: item.anyOf ?? configuredRule?.anyOf,
      };
      if (rule.permission) return hasPermission(rule.permission);
      if (rule.anyOf) return hasAnyPermission(rule.anyOf);
      return true;
    })
    .map(({ key, label, icon }) => ({ key, label, icon }));
  const userOptions = usersQuery.data?.length
    ? usersQuery.data.map((user) => ({ value: user.id, label: `${user.full_name} <${user.email}>` }))
    : devUserOptions;

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
              options={userOptions}
            />
            <Input
              placeholder="X-User-Id"
              value={currentUserId ?? ""}
              style={{ width: 280 }}
              onChange={(event) => setCurrentUserId(event.target.value || null)}
            />
            <Button onClick={() => void refreshAuth()}>Обновить права</Button>
            <Tag color={permissions.includes("admin.access") ? "green" : "blue"}>{permissions.length} прав</Tag>
            <NotificationsDropdown />
          </Space>
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};
