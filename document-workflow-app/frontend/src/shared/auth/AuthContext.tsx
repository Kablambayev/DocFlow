import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { PropsWithChildren } from "react";
import { useCallback, useMemo, useState } from "react";

import { apiClient, setUserIdHeader } from "../api/axios";
import { AuthContext, type AuthContextValue, type AuthUser } from "./auth-context";

const DEFAULT_DEV_USER_ID = "ac9d2376-34a0-439f-b8fc-319418b9fb57";

const getInitialUserId = () => {
  const storedUserId = localStorage.getItem("docflow_user_id");
  if (storedUserId) return storedUserId;
  setUserIdHeader(DEFAULT_DEV_USER_ID);
  return DEFAULT_DEV_USER_ID;
};

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
  const [currentUserId, setCurrentUserIdState] = useState<string | null>(getInitialUserId);

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

  const permissions = useMemo(() => permissionsQuery.data ?? [], [permissionsQuery.data]);
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
