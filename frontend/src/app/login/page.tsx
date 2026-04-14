"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const { data } = await api.post("/auth/login", { email, password });
      const { data: user } = await api.get("/auth/me", {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      setAuth(data.access_token, user);
      router.push("/");
    } catch {
      setError("Неверный логин или пароль");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-xl bg-white p-8 shadow-lg"
      >
        <h1 className="text-2xl font-bold text-gray-900">Артотека</h1>
        <p className="text-sm text-gray-500">Вход в CRM</p>
        {error && (
          <p className="text-sm text-red-600">{error}</p>
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
          required
        />
        <input
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
          required
        />
        <button
          type="submit"
          className="w-full rounded-lg bg-gray-900 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          Войти
        </button>
      </form>
    </div>
  );
}
