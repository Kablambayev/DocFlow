import { apiClient } from "../../shared/api/axios";

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const getUsers = async () => {
  const { data } = await apiClient.get<UserItem[]>("/users");
  return data;
};

export interface UserPayload {
  email: string;
  full_name: string;
  is_active: boolean;
}

export const createUser = async (payload: UserPayload) => {
  const { data } = await apiClient.post<UserItem>("/users", payload);
  return data;
};

export const updateUser = async (id: string, payload: Partial<UserPayload>) => {
  const { data } = await apiClient.put<UserItem>(`/users/${id}`, payload);
  return data;
};
