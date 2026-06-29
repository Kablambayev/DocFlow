import { AuditOutlined, FileTextOutlined, SettingOutlined, SolutionOutlined } from "@ant-design/icons";
import { createBrowserRouter } from "react-router-dom";

import { AccountingDictionariesPage } from "../pages/accounting/AccountingDictionariesPage";
import { AdminV2Page } from "../pages/admin/AdminV2Page";
import { ApprovalMatrixV2Page } from "../pages/admin/ApprovalMatrixV2Page";
import { ApprovalRoutesV2Page } from "../pages/admin/ApprovalRoutesV2Page";
import { DocumentTypesAdminV2Page } from "../pages/admin/DocumentTypesAdminV2Page";
import { RolesPermissionsPage } from "../pages/admin/RolesPermissionsPage";
import { UsersPage } from "../pages/admin/UsersPage";
import { CreateDocumentV2Page } from "../pages/documents/CreateDocumentV2Page";
import { DocumentCardV2Page } from "../pages/documents/DocumentCardV2Page";
import { DocumentsV2Page } from "../pages/documents/DocumentsV2Page";
import { IntegrationLogsPage } from "../pages/integration/IntegrationLogsPage";
import { MyTasksV2Page } from "../pages/tasks/MyTasksV2Page";
import { TreasuryPaymentRequestsPage } from "../pages/treasury/TreasuryPaymentRequestsPage";
import { RequirePermission } from "../shared/auth/RequirePermission";
import { AppLayoutV2 } from "../shared/ui/AppLayoutV2";

export const menuItems = [
  { key: "/documents", label: "Документы", icon: <FileTextOutlined /> },
  { key: "/tasks", label: "Мои задачи", icon: <SolutionOutlined /> },
  { key: "/treasury/payment-requests", label: "Казначейство", icon: <AuditOutlined /> },
  { key: "/accounting", label: "УпрУчет", icon: <AuditOutlined /> },
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
      { index: true, element: <RequirePermission permission="document.read"><DocumentsV2Page /></RequirePermission> },
      { path: "documents", element: <RequirePermission permission="document.read"><DocumentsV2Page /></RequirePermission> },
      { path: "documents/new", element: <RequirePermission permission="document.create"><CreateDocumentV2Page /></RequirePermission> },
      { path: "documents/:id", element: <RequirePermission anyOf={["document.read", "integration_1c.payment_request.send"]}><DocumentCardV2Page /></RequirePermission> },
      { path: "tasks", element: <RequirePermission anyOf={["task.read", "document.approve"]}><MyTasksV2Page /></RequirePermission> },
      { path: "treasury/payment-requests", element: <RequirePermission permission="treasury.payment_request.read"><TreasuryPaymentRequestsPage /></RequirePermission> },
      { path: "integration/logs", element: <RequirePermission permission="integration.log.read"><IntegrationLogsPage /></RequirePermission> },
      { path: "accounting", element: <RequirePermission permission="accounting.read"><AccountingDictionariesPage /></RequirePermission> },
      { path: "admin", element: <RequirePermission anyOf={["admin.access", "document_type.read", "approval_route.read", "approval_matrix.read", "user.read", "role.read", "permission.read"]}><AdminV2Page /></RequirePermission> },
      { path: "admin/document-types", element: <RequirePermission permission="document_type.read"><DocumentTypesAdminV2Page /></RequirePermission> },
      { path: "admin/routes", element: <RequirePermission permission="approval_route.read"><ApprovalRoutesV2Page /></RequirePermission> },
      { path: "admin/matrix", element: <RequirePermission permission="approval_matrix.read"><ApprovalMatrixV2Page /></RequirePermission> },
      { path: "admin/users", element: <RequirePermission permission="user.read"><UsersPage /></RequirePermission> },
      { path: "admin/roles", element: <RequirePermission anyOf={["role.read", "permission.read"]}><RolesPermissionsPage /></RequirePermission> },
    ],
  },
]);
