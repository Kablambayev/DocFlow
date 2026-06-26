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
