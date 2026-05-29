"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/store";

/**
 * Восстанавливает пользователя (с ролью) после перезагрузки страницы.
 * В localStorage хранится только токен — без этого `user` стартует как null,
 * и админ-пункты меню (Комнаты/Пользователи) пропадают, хотя права есть.
 */
export default function AuthHydrator() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);
  const router = useRouter();

  useEffect(() => {
    if (user) return; // роль уже в памяти (после логина) — ничего не делаем
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!token) {
      router.replace("/login");
      return;
    }
    api
      .get("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => {
        logout();
        router.replace("/login");
      });
  }, [user, setUser, logout, router]);

  return null;
}
