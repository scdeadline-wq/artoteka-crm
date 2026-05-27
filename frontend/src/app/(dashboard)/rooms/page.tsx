"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Save, Trash2, Loader2, X } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore, isAdmin as isAdminRole } from "@/lib/store";
import type { Room } from "@/lib/types";

export default function RoomsPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const canAccess = isAdminRole(user);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (user && !canAccess) router.replace("/artworks");
  }, [user, canAccess, router]);

  const { data: rooms = [], isLoading } = useQuery<Room[]>({
    queryKey: ["rooms"],
    queryFn: () => api.get("/rooms/").then((r) => r.data),
    enabled: canAccess,
  });

  const [newName, setNewName] = useState("");
  const [newSort, setNewSort] = useState("0");
  const [errMsg, setErrMsg] = useState<string | null>(null);
  // Локальные изменения по id: { name?, sort_order? } — переключается на «изменено».
  const [edits, setEdits] = useState<Record<number, { name?: string; sort_order?: number }>>({});

  const create = useMutation({
    mutationFn: () =>
      api.post("/rooms/", {
        name: newName.trim(),
        sort_order: Number(newSort) || 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rooms"] });
      setNewName("");
      setNewSort("0");
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось создать комнату");
    },
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { name?: string; sort_order?: number } }) =>
      api.put(`/rooms/${id}/`, body),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["rooms"] });
      setEdits((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось сохранить");
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/rooms/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rooms"] }),
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось удалить");
    },
  });

  if (!canAccess) return null;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Комнаты</h1>
      <p className="mb-6 text-sm text-gray-500">
        Где физически лежат работы. Используется как фильтр на странице произведений.
      </p>

      {errMsg && (
        <div className="mb-4 flex items-center justify-between rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          <span>{errMsg}</span>
          <button onClick={() => setErrMsg(null)} aria-label="Закрыть">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Форма создания */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!newName.trim()) return;
          create.mutate();
        }}
        className="mb-6 flex flex-wrap items-end gap-3 rounded-xl bg-white p-4 shadow-sm"
      >
        <div className="flex-1 min-w-[200px]">
          <label className="mb-1 block text-xs text-gray-500">Название</label>
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="напр. Комната 1, С-12, Стеллаж 3"
            className="w-full rounded-lg border px-3 py-2 text-sm"
            required
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">Порядок</label>
          <input
            type="number"
            value={newSort}
            onChange={(e) => setNewSort(e.target.value)}
            className="w-20 rounded-lg border px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={!newName.trim() || create.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          {create.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          Добавить
        </button>
      </form>

      {/* Список */}
      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : rooms.length === 0 ? (
        <p className="text-gray-500">Комнат пока нет. Создай первую сверху.</p>
      ) : (
        <div className="overflow-hidden rounded-xl bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-gray-500">
                <th className="px-4 py-3">Название</th>
                <th className="px-4 py-3 w-24">Порядок</th>
                <th className="px-4 py-3 w-44 text-right">Действия</th>
              </tr>
            </thead>
            <tbody>
              {rooms.map((r) => {
                const draft = edits[r.id] || {};
                const name = draft.name ?? r.name;
                const sort = draft.sort_order ?? r.sort_order;
                const changed = (draft.name !== undefined && draft.name !== r.name) ||
                  (draft.sort_order !== undefined && draft.sort_order !== r.sort_order);
                return (
                  <tr key={r.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <input
                        value={name}
                        onChange={(e) =>
                          setEdits((prev) => ({
                            ...prev,
                            [r.id]: { ...prev[r.id], name: e.target.value },
                          }))
                        }
                        className="w-full rounded border px-2 py-1.5 text-sm"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="number"
                        value={sort}
                        onChange={(e) =>
                          setEdits((prev) => ({
                            ...prev,
                            [r.id]: { ...prev[r.id], sort_order: Number(e.target.value) || 0 },
                          }))
                        }
                        className="w-20 rounded border px-2 py-1.5 text-sm"
                      />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <div className="inline-flex gap-2">
                        <button
                          onClick={() => {
                            if (!changed) return;
                            const body: { name?: string; sort_order?: number } = {};
                            if (draft.name !== undefined && draft.name !== r.name) {
                              body.name = (draft.name || "").trim();
                              if (!body.name) return;
                            }
                            if (draft.sort_order !== undefined && draft.sort_order !== r.sort_order) {
                              body.sort_order = draft.sort_order;
                            }
                            update.mutate({ id: r.id, body });
                          }}
                          disabled={!changed || update.isPending}
                          className="flex items-center gap-1 rounded border border-blue-300 px-2.5 py-1 text-xs text-blue-700 hover:bg-blue-50 disabled:opacity-30"
                        >
                          <Save size={12} /> Сохранить
                        </button>
                        <button
                          onClick={() => {
                            if (!confirm(`Удалить комнату «${r.name}»?\nРаботы в ней останутся, но потеряют привязку к комнате.`)) {
                              return;
                            }
                            remove.mutate(r.id);
                          }}
                          disabled={remove.isPending}
                          className="flex items-center gap-1 rounded border border-red-300 px-2.5 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-30"
                        >
                          <Trash2 size={12} /> Удалить
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
