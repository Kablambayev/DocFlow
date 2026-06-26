import { AuditOutlined, FileTextOutlined, SettingOutlined, SolutionOutlined } from "@ant-design/icons";
import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "../shared/ui/AppLayout";
import { AdminPage } from "../pages/admin/AdminPage";
import { ApprovalMatrixBuilderPage } from "../pages/admin/ApprovalMatrixBuilderPage";
import { ApprovalRoutesBuilderPage } from "../pages/admin/ApprovalRoutesBuilderPage";
import { DocumentTypesAdminPage } from "../pages/admin/DocumentTypesAdminPage";
import { CreateDocumentBySchemaPage } from "../pages/documents/CreateDocumentBySchemaPage";
import { DocumentCardEnhancedPage } from "../pages/documents/DocumentCardEnhancedPage";
import { DocumentsPage } from "../pages/documents/DocumentsPage";
import { MyTasksPage } from "../pages/tasks/MyTasksPage";

export const menuItems = [
  { key: "/documents", label: "Документы", icon: <FileTextOutlined /> },
  { key: "/tasks", label: "Мои задачи", icon: <SolutionOutlined /> },
  { key: "/admin", label: "Администрирование", icon: <SettingOutlined /> },
  { key: "/admin/document-types", label: "Типы документов", icon: <AuditOutlined /> },
  { key: "/admin/routes", label: "Маршруты", icon: <AuditOutlined /> },
  { key: "/admin/matrix", label: "Матрица согласования", icon: <AuditOutlined /> },
];

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout menuItems={menuItems} />,
    children: [
      { index: true, element: <DocumentsPage /> },
      { path: "documents", element: <DocumentsPage /> },
      { path: "documents/new", element: <CreateDocumentBySchemaPage /> },
      { path: "documents/:id", element: <DocumentCardEnhancedPage /> },
      { path: "tasks", element: <MyTasksPage /> },
      { path: "admin", element: <AdminPage /> },
      { path: "admin/document-types", element: <DocumentTypesAdminPage /> },
      { path: "admin/routes", element: <ApprovalRoutesBuilderPage /> },
      { path: "admin/matrix", element: <ApprovalMatrixBuilderPage /> },
    ],
  },
]);
