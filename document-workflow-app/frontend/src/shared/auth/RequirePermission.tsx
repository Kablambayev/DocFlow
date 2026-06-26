import { Alert, Card, Spin } from "antd";
import type { PropsWithChildren } from "react";

import { useAuth } from "./useAuth";

interface RequirePermissionProps extends PropsWithChildren {
  permission?: string;
  anyOf?: string[];
}

export const RequirePermission = ({ permission, anyOf, children }: RequirePermissionProps) => {
  const { currentUserId, hasPermission, hasAnyPermission, isLoading } = useAuth();

  if (!currentUserId) {
    return (
      <Card>
        <Alert type="warning" showIcon message="Выберите dev-пользователя в шапке приложения" />
      </Card>
    );
  }

  if (isLoading) {
    return <Spin />;
  }

  const allowed = permission ? hasPermission(permission) : hasAnyPermission(anyOf ?? []);
  if (!allowed) {
    return (
      <Card>
        <Alert type="error" showIcon message="Недостаточно прав для открытия раздела" />
      </Card>
    );
  }

  return <>{children}</>;
};
