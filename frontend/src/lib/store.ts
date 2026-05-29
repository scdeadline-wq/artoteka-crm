import { create } from "zustand";

export type UserRole = "owner" | "admin" | "manager" | "viewer";

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  setAuth: (token: string, user: AuthState["user"]) => void;
  setUser: (user: AuthUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("token") : null,
  user: null,
  setAuth: (token, user) => {
    localStorage.setItem("token", token);
    set({ token, user });
  },
  // Восстановление пользователя по живому токену (роль не персистится — тянем /auth/me).
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, user: null });
  },
}));

// owner и admin — обе админские роли (видят закупку, могут CRUD/удаление/комнаты/пользователей).
// Назначать роль owner может только owner.
export const isAdmin = (user: AuthUser | null): boolean =>
  user?.role === "owner" || user?.role === "admin";

export const isOwner = (user: AuthUser | null): boolean =>
  user?.role === "owner";
