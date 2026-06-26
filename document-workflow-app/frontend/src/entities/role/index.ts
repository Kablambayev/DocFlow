import { apiClient } from "../../shared/api/axios";

export interface PermissionItem {
  id: string;
  code: string;
  name: string;
  description: string | null;
}

export interface RoleItem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  permissions: PermissionItem[];
}

export interface RolePayload {
  code: string;
  name: string;
  description?: string | null;
  is_active: boolean;
}

export const getRoles = async () => {
  const { data } = await apiClient.get<RoleItem[]>("/roles");
  return data;
};

export const createRole = async (payload: RolePayload) => {
  const { data } = await apiClient.post<RoleItem>("/roles", payload);
  return data;
};

export const updateRole = async (id: string, payload: Partial<RolePayload>) => {
  const { data } = await apiClient.put<RoleItem>(`/roles/${id}`, payload);
  return data;
};

export const getPermissions = async () => {
  const { data } = await apiClient.get<PermissionItem[]>("/permissions");
  return data;
};

export const addRolePermission = async (roleId: string, permissionId: string) => {
  const { data } = await apiClient.post<RoleItem>(`/roles/${roleId}/permissions`, { permission_id: permissionId });
  return data;
};

export const removeRolePermission = async (roleId: string, permissionId: string) => {
  const { data } = await apiClient.delete<RoleItem>(`/roles/${roleId}/permissions/${permissionId}`);
  return data;
};

export const getUserRoles = async (userId: string) => {
  const { data } = await apiClient.get<RoleItem[]>(`/users/${userId}/roles`);
  return data;
};

export const addUserRole = async (userId: string, roleId: string) => {
  const { data } = await apiClient.post<RoleItem[]>(`/users/${userId}/roles`, { role_id: roleId });
  return data;
};

export const removeUserRole = async (userId: string, roleId: string) => {
  const { data } = await apiClient.delete<RoleItem[]>(`/users/${userId}/roles/${roleId}`);
  return data;
};
