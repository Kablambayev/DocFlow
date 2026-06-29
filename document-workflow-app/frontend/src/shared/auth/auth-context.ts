import { createContext } from "react";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface AuthContextValue {
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
