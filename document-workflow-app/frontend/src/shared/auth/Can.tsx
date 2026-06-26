import type { PropsWithChildren, ReactNode } from "react";

import { useAuth } from "./useAuth";

interface CanProps extends PropsWithChildren {
  permission?: string;
  anyOf?: string[];
  fallback?: ReactNode;
}

export const Can = ({ permission, anyOf, fallback = null, children }: CanProps) => {
  const { hasPermission, hasAnyPermission } = useAuth();
  const allowed = permission ? hasPermission(permission) : hasAnyPermission(anyOf ?? []);
  return allowed ? <>{children}</> : <>{fallback}</>;
};
