import { AuditOutlined, FileTextOutlined, SettingOutlined, SolutionOutlined } from "@ant-design/icons";
import { createBrowserRouter } from "react-router-dom";

import { AdminV2Page } from "../pages/admin/AdminV2Page";
import { ApprovalMatrixV2Page } from "../pages/admin/ApprovalMatrixV2Page";
import { ApprovalRoutesV2Page } from "../pages/admin/ApprovalRoutesV2Page";
import { DocumentTypesAdminV2Page } from "../pages/admin/DocumentTypesAdminV2Page";
import { UsersPage } from "../pages/admin/UsersPage";
import { DocumentCardV2Page } from "../pages/documents/DocumentCardV2Page";
import { CreateDocumentV2Page } from "../pages/documents/CreateDocumentV2Page";
import { DocumentsV2Page } from "../pages/documents/DocumentsV2Page";
import { MyTasksV2Page } from "../pages/tasks/MyTasksV2Page";
import { AppLayoutV2 } from "../shared/ui/AppLayoutV2";

export const menuItems = [
  { key: "/documents", label: "Документы", icon: <FileTextOutlined /> },
  { key: "/tasks", label: "Мои задачи", icon: <SolutionOutlined /> },
  { key: "/admin", label: "Администрирование", icon: <SettingOutlined /> },
  { key: "/admin/document-types", label: "Типы документов", icon: <AuditOutlined /> },
  { key: "/admin/routes", label: "Маршруты согласования", icon: <AuditOutlined /> },
  { key: "/admin/matrix", label: "Матрица согласования", icon: <AuditOutlined /> },
  { key: "/admin/users", label: "Пользователи", icon: <AuditOutlined /> },
];

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayoutV2 menuItems={menuItems} />,
    children: [
      { index: true, element: <DocumentsV2Page /> },
      { path: "documents", element: <DocumentsV2Page /> },
      { path: "documents/new", element: <CreateDocumentV2Page /> },
      { path: "documents/:id", element: <DocumentCardV2Page /> },
      { path: "tasks", element: <MyTasksV2Page /> },
      { path: "admin", element: <AdminV2Page /> },
      { path: "admin/document-types", element: <DocumentTypesAdminV2Page /> },
      { path: "admin/routes", element: <ApprovalRoutesV2Page /> },
      { path: "admin/matrix", element: <ApprovalMatrixV2Page /> },
      { path: "admin/users", element: <UsersPage /> },
    ],
  },
]);
