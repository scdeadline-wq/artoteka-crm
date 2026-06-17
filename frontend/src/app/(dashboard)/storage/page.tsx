"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Loader2 } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore, isAdmin as isAdminRole } from "@/lib/store";
import type { StorageOption, Room } from "@/lib/types";

const KINDS: { kind: string; title: string; placeholder: string }[] = [
  { kind: "warehouse", title: "Склады / адреса", placeholder: "напр. Склад на Тверской" },
  { kind: "rack", title: "Стеллажи", placeholder: "напр. Стеллаж 3" },
  { kind: "shelf", title: "Полки", placeholder: "напр. Полка 2" },
];

// Комнаты — отдельная сущность (используется в фильтрах/вкладках), но управляется здесь же.
function RoomsSection() {
  const queryClient = useQueryClient();
  const [newName, setNewName] = useState("");
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const { data: items = [] } = useQuery<Room[]>({
    queryKey: ["rooms"],
    queryFn: () => api.get("/rooms/").then((r) => r.data),
  });
  const create = useMutation({
    mutationFn: () => api.post("/rooms/", { name: newName.trim() }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["rooms"] }); setNewName(""); setErrMsg(null); },
    onError: (e: { response?: { data?: { detail?: string } } }) => setErrMsg(e?.response?.data?.detail || "Не удалось добавить"),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/rooms/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rooms"] }),
    onError: (e: { response?: { data?: { detail?: string } } }) => setErrMsg(e?.response?.data?.detail || "Не удалось удалить"),
  });

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-gray-700">Комнаты</h2>
      {errMsg && <p className="mb-2 text-xs text-red-600">{errMsg}</p>}
      <form onSubmit={(e) => { e.preventDefault(); if (newName.trim()) create.mutate(); }} className="mb-3 flex gap-2">
        <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="напр. Кабинет Паруйра" className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm" />
        <button type="submit" disabled={!newName.trim() || create.isPending} className="flex items-center gap-1 rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50">
          {create.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
        </button>
      </form>
      {items.length === 0 ? (
        <p className="text-xs text-gray-400">Пока пусто</p>
      ) : (
        <ul className="divide-y">
          {items.map((it) => (
            <li key={it.id} className="flex items-center justify-between py-2 text-sm">
              <span className="text-gray-800">{it.name}</span>
              <button onClick={() => { if (confirm(`Удалить «${it.name}»?\nУ работ привязка к этой комнате обнулится.`)) remove.mutate(it.id); }} className="text-gray-300 hover:text-red-600" aria-label="Удалить">
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StorageKindSection({ kind, title, placeholder }: { kind: string; title: string; placeholder: string }) {
  const queryClient = useQueryClient();
  const [newName, setNewName] = useState("");
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const { data: items = [] } = useQuery<StorageOption[]>({
    queryKey: ["storage", kind],
    queryFn: () => api.get(`/storage/?kind=${kind}`).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () => api.post("/storage/", { kind, name: newName.trim() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storage", kind] });
      setNewName("");
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      setErrMsg(e?.response?.data?.detail || "Не удалось добавить"),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/storage/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["storage", kind] }),
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      setErrMsg(e?.response?.data?.detail || "Не удалось удалить"),
  });

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-gray-700">{title}</h2>
      {errMsg && <p className="mb-2 text-xs text-red-600">{errMsg}</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (newName.trim()) create.mutate();
        }}
        className="mb-3 flex gap-2"
      >
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={!newName.trim() || create.isPending}
          className="flex items-center gap-1 rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          {create.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
        </button>
      </form>
      {items.length === 0 ? (
        <p className="text-xs text-gray-400">Пока пусто</p>
      ) : (
        <ul className="divide-y">
          {items.map((it) => (
            <li key={it.id} className="flex items-center justify-between py-2 text-sm">
              <span className="text-gray-800">{it.name}</span>
              <button
                onClick={() => {
                  if (confirm(`Удалить «${it.name}»?\nУ работ привязка к этому месту обнулится.`)) remove.mutate(it.id);
                }}
                className="text-gray-300 hover:text-red-600"
                aria-label="Удалить"
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function StoragePage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const canAccess = isAdminRole(user);

  useEffect(() => {
    if (user && !canAccess) router.replace("/artworks");
  }, [user, canAccess, router]);

  if (!canAccess) return null;

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Хранение</h1>
      <p className="mb-6 text-sm text-gray-500">
        Справочники мест хранения и комнат. Эти значения менеджер выбирает из списков
        при добавлении работы.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {KINDS.map((k) => (
          <StorageKindSection key={k.kind} {...k} />
        ))}
        <RoomsSection />
      </div>
    </div>
  );
}
