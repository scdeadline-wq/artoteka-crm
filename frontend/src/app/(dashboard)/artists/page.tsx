"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import api from "@/lib/api";
import type { Artist } from "@/lib/types";

export default function ArtistsPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [nameRu, setNameRu] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [isGroup, setIsGroup] = useState(false);

  const [search, setSearch] = useState("");
  const [groupFilter, setGroupFilter] = useState<"all" | "single" | "group">("all");

  const { data: artists = [] } = useQuery<Artist[]>({
    queryKey: ["artists", search, groupFilter],
    queryFn: () =>
      api
        .get("/artists", {
          params: {
            q: search || undefined,
            is_group: groupFilter === "all" ? undefined : groupFilter === "group",
          },
        })
        .then((r) => r.data),
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
    },
  });

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
                  <li
                    key={a.id}
                    className="flex items-center gap-4 border-b px-4 py-2.5 text-sm last:border-0 hover:bg-gray-50"
                  >
                    <span className="font-medium text-gray-900">{a.name_ru}</span>
                    {a.name_en && (
                      <span className="text-gray-500">{a.name_en}</span>
                    )}
                    {a.is_group && (
                      <span className="ml-auto rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                        группа
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
