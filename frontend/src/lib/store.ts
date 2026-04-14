import { create } from "zustand";

interface AuthState {
  token: string | null;
  user: { id: number; name: string; email: string; role: string } | null;
  setAuth: (token: string, user: AuthState["user"]) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("token") : null,
  user: null,
  setAuth: (token, user) => {
    localStorage.setItem("token", token);
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, user: null });
  },
}));
