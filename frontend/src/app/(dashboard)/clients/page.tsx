"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Edit3, X, Save, Search, Trash2, Eye, Loader2 } from "lucide-react";
import Link from "next/link";
import { AxiosError } from "axios";
import api from "@/lib/api";
import type { Client, ClientDetail, Artist } from "@/lib/types";
import { CLIENT_TYPE_LABELS } from "@/lib/types";

const TYPES = ["buyer", "dealer", "referral"] as const;

export default function ClientsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [viewId, setViewId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Client | null>(null);

  const { data: clients = [] } = useQuery<Client[]>({
    queryKey: ["clients", search, typeFilter],
    queryFn: () =>
      api.get("/clients", { params: { q: search || undefined, client_type: typeFilter || undefined } }).then((r) => r.data),
  });

  const { data: viewClient, isLoading: viewLoading } = useQuery<ClientDetail>({
    queryKey: ["client", viewId],
    queryFn: () => api.get(`/clients/${viewId}/`).then((r) => r.data),
    enabled: viewId !== null,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/clients/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setDeleteTarget(null);
    },
    onError: (err: AxiosError<{ detail?: string }>) => {
      alert(err.response?.data?.detail || "Не удалось удалить клиента");
      setDeleteTarget(null);
    },
  });

  const { data: artists = [] } = useQuery<Artist[]>({
    queryKey: ["artists"],
    queryFn: () => api.get("/artists").then((r) => r.data),
  });

  const emptyForm = {
    name: "",
    phone: "",
    email: "",
    telegram: "",
    client_type: "buyer",
    description: "",
    preferred_artist_ids: [] as number[],
  };

  const [form, setForm] = useState(emptyForm);

  const createMutation = useMutation({
    mutationFn: () => api.post("/clients", form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setShowCreate(false);
      setForm(emptyForm);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (id: number) => api.put(`/clients/${id}`, form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setEditingId(null);
    },
  });

  function startEdit(c: Client) {
    setForm({
      name: c.name,
      phone: c.phone || "",
      email: c.email || "",
      telegram: c.telegram || "",
      client_type: c.client_type,
      description: c.description || "",
      preferred_artist_ids: c.preferred_artists.map((a) => a.id),
    });
    setEditingId(c.id);
    setShowCreate(false);
  }

  function toggleArtist(id: number) {
    setForm((f) => ({
      ...f,
      preferred_artist_ids: f.preferred_artist_ids.includes(id)
        ? f.preferred_artist_ids.filter((x) => x !== id)
        : [...f.preferred_artist_ids, id],
    }));
  }

  const formUI = (
    <div className="space-y-3 rounded-xl bg-white p-5 shadow-sm">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-gray-500">Имя *</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-lg border px-3 py-2 text-sm" required />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">Телефон</label>
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="w-full rounded-lg border px-3 py-2 text-sm" placeholder="+7..." />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">Telegram</label>
          <input value={form.telegram} onChange={(e) => setForm({ ...form, telegram: e.target.value })} className="w-full rounded-lg border px-3 py-2 text-sm" placeholder="@username" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">Тип</label>
          <select value={form.client_type} onChange={(e) => setForm({ ...form, client_type: e.target.value })} className="w-full rounded-lg border px-3 py-2 text-sm">
            {TYPES.map((t) => <option key={t} value={t}>{CLIENT_TYPE_LABELS[t]}</option>)}
          </select>
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs text-gray-500">Описание / заметки</label>
        <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} className="w-full rounded-lg border px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-2 block text-xs text-gray-500">Предпочтения по художникам</label>
        <div className="flex flex-wrap gap-1.5">
          {artists.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => toggleArtist(a.id)}
              className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                form.preferred_artist_ids.includes(a.id)
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {a.name_ru}
            </button>
          ))}
          {artists.length === 0 && <span className="text-xs text-gray-400">Сначала добавьте художников</span>}
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => editingId ? updateMutation.mutate(editingId) : createMutation.mutate()}
          disabled={!form.name || createMutation.isPending || updateMutation.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          <Save size={14} /> {editingId ? "Сохранить" : "Создать"}
        </button>
        <button
          onClick={() => { setEditingId(null); setShowCreate(false); setForm(emptyForm); }}
          className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
        >
          Отмена
        </button>
      </div>
    </div>
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Клиенты</h1>
        <button
          onClick={() => { setShowCreate(true); setEditingId(null); setForm(emptyForm); }}
          className="flex items-center gap-2 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          <Plus size={16} /> Добавить
        </button>
      </div>

      <div className="mb-4 flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            placeholder="Поиск..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border py-2 pl-9 pr-4 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="rounded-lg border px-3 py-2 text-sm">
          <option value="">Все типы</option>
          {TYPES.map((t) => <option key={t} value={t}>{CLIENT_TYPE_LABELS[t]}</option>)}
        </select>
      </div>

      {(showCreate || editingId) && <div className="mb-4">{formUI}</div>}

      <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-gray-500">
              <th className="px-4 py-3">Имя</th>
              <th className="px-4 py-3">Тип</th>
              <th className="px-4 py-3">Телефон</th>
              <th className="px-4 py-3">Telegram</th>
              <th className="px-4 py-3">Предпочтения</th>
              <th className="px-4 py-3 w-28"></th>
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id} className={`border-b last:border-0 hover:bg-gray-50 ${editingId === c.id ? "bg-blue-50" : ""}`}>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setViewId(c.id)}
                    className="font-medium text-gray-900 hover:text-blue-600 hover:underline"
                  >
                    {c.name}
                  </button>
                  {c.description && (
                    <p className="mt-0.5 max-w-xs truncate text-xs text-gray-400">{c.description}</p>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs">
                    {CLIENT_TYPE_LABELS[c.client_type] || c.client_type}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{c.phone || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{c.telegram || "—"}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {c.preferred_artists.map((a) => a.name_ru).join(", ") || "—"}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <button
                      onClick={() => setViewId(c.id)}
                      title="Карточка клиента"
                      className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      onClick={() => startEdit(c)}
                      title="Редактировать"
                      className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                    >
                      <Edit3 size={14} />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(c)}
                      title="Удалить"
                      className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {clients.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Нет клиентов</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Карточка клиента */}
      {viewId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setViewId(null)}>
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            {viewLoading || !viewClient ? (
              <div className="flex items-center justify-center py-10 text-gray-400">
                <Loader2 size={20} className="animate-spin" />
              </div>
            ) : (
              <>
                <div className="mb-4 flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{viewClient.name}</h2>
                    <span className="mt-1 inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {CLIENT_TYPE_LABELS[viewClient.client_type] || viewClient.client_type}
                    </span>
                  </div>
                  <button onClick={() => setViewId(null)} className="rounded p-1 text-gray-400 hover:bg-gray-100">
                    <X size={18} />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-gray-500">Телефон</p>
                    <p className="font-medium">{viewClient.phone || "—"}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Email</p>
                    <p className="font-medium">{viewClient.email || "—"}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Telegram</p>
                    <p className="font-medium">{viewClient.telegram || "—"}</p>
                  </div>
                </div>

                {viewClient.description && (
                  <div className="mt-4 border-t pt-3">
                    <p className="mb-1 text-sm text-gray-500">Описание / заметки</p>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">{viewClient.description}</p>
                  </div>
                )}

                {viewClient.preferred_artists.length > 0 && (
                  <div className="mt-4 border-t pt-3">
                    <p className="mb-1 text-sm text-gray-500">Предпочтения по художникам</p>
                    <p className="text-sm text-gray-700">{viewClient.preferred_artists.map((a) => a.name_ru).join(", ")}</p>
                  </div>
                )}

                <div className="mt-4 border-t pt-3">
                  <p className="mb-2 text-sm text-gray-500">
                    Покупки ({viewClient.purchases.length})
                  </p>
                  {viewClient.purchases.length === 0 ? (
                    <p className="text-sm text-gray-400">Пока нет покупок</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {viewClient.purchases.map((p) => (
                        <li key={p.id} className="flex items-center justify-between text-sm">
                          <Link
                            href={`/artworks/${p.artwork_id}`}
                            className="text-gray-700 hover:text-blue-600 hover:underline"
                          >
                            {p.artist_name ? `${p.artist_name} — ` : ""}{p.artwork_title || "Без названия"}
                          </Link>
                          <span className="whitespace-nowrap text-gray-500">
                            {Number(p.sold_price).toLocaleString("ru")} ₽ · {new Date(p.sold_at).toLocaleDateString("ru")}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="mt-5 flex gap-2">
                  <button
                    onClick={() => { const c = clients.find((x) => x.id === viewClient.id); setViewId(null); if (c) startEdit(c); }}
                    className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
                  >
                    <Edit3 size={14} /> Редактировать
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Подтверждение удаления */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-bold text-gray-900">Удалить клиента?</h2>
            <p className="mb-4 text-sm text-gray-700">«{deleteTarget.name}»</p>
            <p className="mb-4 text-xs text-gray-500">
              Если за клиентом числятся покупки, удаление будет запрещено — история продаж сохраняется.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
                disabled={deleteMutation.isPending}
                className="flex-1 rounded-lg bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Удаляю..." : "Удалить"}
              </button>
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
