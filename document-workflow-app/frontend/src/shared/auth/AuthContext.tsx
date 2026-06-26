import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { PropsWithChildren } from "react";
import { createContext, useCallback, useMemo, useState } from "react";

import { apiClient, setUserIdHeader } from "../api/axios";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

interface AuthContextValue {
  currentUser: AuthUser | null;
  currentUserId: string | null;
  permissions: string[];
  isLoading: boolean;
  isAdmin: boolean;
  setCurrentUserId: (userId: string | null) => void;
  refreshAuth: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

const getMe = async () => {
  const { data } = await apiClient.get<AuthUser>("/me");
  return data;
};

const getMyPermissions = async () => {
  const { data } = await apiClient.get<string[]>("/me/permissions");
  return data;
};

export const AuthProvider = ({ children }: PropsWithChildren) => {
  const queryClient = useQueryClient();
  const [currentUserId, setCurrentUserIdState] = useState(() => localStorage.getItem("docflow_user_id"));

  const meQuery = useQuery({
    queryKey: ["auth", "me", currentUserId],
    queryFn: getMe,
    enabled: Boolean(currentUserId),
    retry: false,
  });

  const permissionsQuery = useQuery({
    queryKey: ["auth", "permissions", currentUserId],
    queryFn: getMyPermissions,
    enabled: Boolean(currentUserId),
    retry: false,
  });

  const setCurrentUserId = useCallback(
    (userId: string | null) => {
      setUserIdHeader(userId);
      setCurrentUserIdState(userId);
      void queryClient.invalidateQueries();
    },
    [queryClient],
  );

  const refreshAuth = useCallback(async () => {
    await Promise.all([meQuery.refetch(), permissionsQuery.refetch()]);
  }, [meQuery, permissionsQuery]);

  const permissions = permissionsQuery.data ?? [];
  const hasPermission = useCallback(
    (permission: string) => permissions.includes("admin.access") || permissions.includes(permission),
    [permissions],
  );
  const hasAnyPermission = useCallback(
    (items: string[]) => permissions.includes("admin.access") || items.some((permission) => permissions.includes(permission)),
    [permissions],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      currentUser: meQuery.data ?? null,
      currentUserId,
      permissions,
      isLoading: meQuery.isLoading || permissionsQuery.isLoading,
      isAdmin: permissions.includes("admin.access"),
      setCurrentUserId,
      refreshAuth,
      hasPermission,
      hasAnyPermission,
    }),
    [currentUserId, hasAnyPermission, hasPermission, meQuery.data, meQuery.isLoading, permissions, permissionsQuery.isLoading, refreshAuth, setCurrentUserId],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
