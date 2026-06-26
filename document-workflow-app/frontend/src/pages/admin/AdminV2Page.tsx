import { Card, List, Typography } from "antd";
import { Link } from "react-router-dom";

const items = [
  { to: "/accounting", label: "УпрУчет" },
  { to: "/admin/document-types", label: "Типы документов" },
  { to: "/admin/routes", label: "Маршруты согласования" },
  { to: "/admin/matrix", label: "Матрица согласования" },
  { to: "/admin/users", label: "Пользователи" },
];

export const AdminV2Page = () => (
  <Card>
    <Typography.Title level={4}>Администрирование</Typography.Title>
    <List dataSource={items} renderItem={(item) => <List.Item><Link to={item.to}>{item.label}</Link></List.Item>} />
  </Card>
);
