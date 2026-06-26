import { Layout, Menu, Typography } from "antd";
import type { PropsWithChildren } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

const { Header, Sider, Content } = Layout;

type MenuItem = {
  key: string;
  label: string;
  icon?: React.ReactNode;
};

interface AppLayoutProps extends PropsWithChildren {
  menuItems: MenuItem[];
}

export const AppLayoutV2 = ({ menuItems }: AppLayoutProps) => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Layout style={{ minHeight: "100vh", background: "linear-gradient(180deg, #f3f6f7 0%, #e9efee 100%)" }}>
      <Sider width={280} theme="light" style={{ borderRight: "1px solid #d8e2e0" }}>
        <div style={{ padding: 20 }}>
          <Typography.Title level={4} style={{ margin: 0, color: "#0a6e6e" }}>
            DocFlow
          </Typography.Title>
          <Typography.Text type="secondary">ЭДО и согласования</Typography.Text>
        </div>
        <Menu selectedKeys={[location.pathname]} mode="inline" items={menuItems} onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout>
        <Header style={{ background: "#ffffff", borderBottom: "1px solid #d8e2e0", padding: "0 20px" }}>
          <Typography.Title level={5} style={{ margin: "16px 0" }}>
            Управление документами
          </Typography.Title>
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};
