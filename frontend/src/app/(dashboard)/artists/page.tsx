"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { Plus, Search, Edit3, Save, X } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { useDebounced } from "@/lib/use-debounced";
import type { Artist } from "@/lib/types";

export default function ArtistsPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [nameRu, setNameRu] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [isGroup, setIsGroup] = useState(false);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [editing, setEditing] = useState<Artist | null>(null);
  const [editForm, setEditForm] = useState({ name_ru: "", name_en: "", is_group: false, bio: "" });

  const [search, setSearch] = useState("");
  const [groupFilter, setGroupFilter] = useState<"all" | "single" | "group">("all");
  const debouncedSearch = useDebounced(search);

  const { data: artists = [] } = useQuery<Artist[]>({
    queryKey: ["artists", debouncedSearch, groupFilter],
    queryFn: () =>
      api
        .get("/artists", {
          params: {
            q: debouncedSearch || undefined,
            is_group: groupFilter === "all" ? undefined : groupFilter === "group",
          },
        })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
  });

  // Фамилия = ПОСЛЕДНЕЕ слово name_ru (данные в формате «Имя Фамилия»),
  // скобочные пояснения отбрасываем: «Алексей Смирнов (фон Раух)» → «Смирнов».
  const surnameOf = (a: Artist) => {
    const cleaned = a.name_ru.replace(/\s*\([^)]*\)/g, "").trim();
    const parts = cleaned.split(/\s+/);
    return parts[parts.length - 1] || cleaned;
  };

  // Сортируем по фамилии, затем группируем по её первой букве.
  const grouped = (() => {
    const sorted = [...artists].sort((a, b) =>
      surnameOf(a).localeCompare(surnameOf(b), "ru")
    );
    const groups = new Map<string, Artist[]>();
    for (const a of sorted) {
      const first = surnameOf(a).charAt(0).toUpperCase();
      const letter = /[A-ZА-ЯЁ]/u.test(first) ? first : "#";
      const arr = groups.get(letter);
      if (arr) arr.push(a);
      else groups.set(letter, [a]);
    }
    return Array.from(groups.entries()).sort(([a], [b]) => {
      if (a === "#") return 1;
      if (b === "#") return -1;
      return a.localeCompare(b, "ru");
    });
  })();

  const create = useMutation({
    mutationFn: () =>
      api.post("/artists", { name_ru: nameRu, name_en: nameEn || null, is_group: isGroup }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artists"] });
      setShowForm(false);
      setNameRu("");
      setNameEn("");
      setIsGroup(false);
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось создать художника");
    },
  });

  const update = useMutation({
    mutationFn: (id: number) =>
      api.put(`/artists/${id}/`, {
        name_ru: editForm.name_ru,
        name_en: editForm.name_en || null,
        is_group: editForm.is_group,
        bio: editForm.bio || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artists"] });
      setEditing(null);
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось сохранить художника");
    },
  });

  function startEdit(a: Artist) {
    setEditForm({
      name_ru: a.name_ru,
      name_en: a.name_en || "",
      is_group: a.is_group,
      bio: a.bio || "",
    });
    setEditing(a);
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Художники</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          <Plus size={16} />
          Добавить
        </button>
      </div>

      {errMsg && (
        <div className="mb-4 flex items-center justify-between rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          <span>{errMsg}</span>
          <button onClick={() => setErrMsg(null)} aria-label="Закрыть">
            <X size={14} />
          </button>
        </div>
      )}

      {showForm && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
          className="mb-6 flex flex-wrap items-end gap-3 rounded-xl bg-white p-4 shadow-sm"
        >
          <div>
            <label className="mb-1 block text-xs text-gray-500">Имя (рус)</label>
            <input
              value={nameRu}
              onChange={(e) => setNameRu(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Имя (англ)</label>
            <input
              value={nameEn}
              onChange={(e) => setNameEn(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isGroup}
              onChange={(e) => setIsGroup(e.target.checked)}
            />
            Группа
          </label>
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
          >
            Сохранить
          </button>
        </form>
      )}

      <div className="mb-4 flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            placeholder="Поиск по имени..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border py-2 pl-9 pr-4 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <select
          value={groupFilter}
          onChange={(e) => setGroupFilter(e.target.value as "all" | "single" | "group")}
          className="rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="all">Все</option>
          <option value="single">Одиночки</option>
          <option value="group">Группы</option>
        </select>
      </div>

      {artists.length === 0 ? (
        <p className="py-6 text-center text-gray-400">Никого не нашли</p>
      ) : (
        <div className="space-y-4">
          {grouped.map(([letter, items]) => (
            <section key={letter} className="rounded-xl bg-white shadow-sm">
              <header className="border-b px-4 py-2 text-sm font-semibold text-gray-500">
                {letter}
                <span className="ml-2 text-xs font-normal text-gray-400">
                  {items.length}
                </span>
              </header>
              <ul>
                {items.map((a) => (
                  <li key={a.id} className="flex items-center border-b last:border-0 hover:bg-gray-50">
                    <Link
                      href={`/artworks?artist=${a.id}`}
                      className="flex flex-1 items-center gap-4 px-4 py-2.5 text-sm"
                      title="Показать работы этого художника"
                    >
                      <span className="font-medium text-gray-900 hover:text-blue-600">
                        {a.name_ru}
                      </span>
                      {a.name_en && (
                        <span className="text-gray-500">{a.name_en}</span>
                      )}
                      {a.is_group && (
                        <span className="ml-auto rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                          группа
                        </span>
                      )}
                    </Link>
                    <button
                      onClick={() => startEdit(a)}
                      title="Редактировать"
                      className="mr-3 rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                    >
                      <Edit3 size={14} />
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      {/* Модалка редактирования художника */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setEditing(null)}>
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-start justify-between">
              <h2 className="text-xl font-bold text-gray-900">Редактировать художника</h2>
              <button onClick={() => setEditing(null)} className="rounded p-1 text-gray-400 hover:bg-gray-100">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs text-gray-500">Имя (рус) *</label>
                  <input
                    value={editForm.name_ru}
                    onChange={(e) => setEditForm({ ...editForm, name_ru: e.target.value })}
                    className="w-full rounded-lg border px-3 py-2 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-gray-500">Имя (англ)</label>
                  <input
                    value={editForm.name_en}
                    onChange={(e) => setEditForm({ ...editForm, name_en: e.target.value })}
                    className="w-full rounded-lg border px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={editForm.is_group}
                  onChange={(e) => setEditForm({ ...editForm, is_group: e.target.checked })}
                />
                Группа
              </label>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Биография</label>
                <textarea
                  value={editForm.bio}
                  onChange={(e) => setEditForm({ ...editForm, bio: e.target.value })}
                  rows={5}
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="mt-5 flex gap-2">
              <button
                onClick={() => update.mutate(editing.id)}
                disabled={!editForm.name_ru.trim() || update.isPending}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                <Save size={14} /> {update.isPending ? "Сохраняю..." : "Сохранить"}
              </button>
              <button
                onClick={() => setEditing(null)}
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
