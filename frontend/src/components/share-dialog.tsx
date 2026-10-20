"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Copy, Check, ExternalLink, Trash2, X, Search } from "lucide-react";
import api from "@/lib/api";
import { copyText, shareUrl, worksLabel } from "@/lib/share";
import type { Artist, ShareLink } from "@/lib/types";

// Ссылка на подборку для клиента: по художникам и/или тегам, без них — весь каталог. Подборка «живая» —
// новые работы автора/с тегом появляются по той же ссылке сами.
export default function ShareDialog({
  artists,
  initialArtistId,
  initialTag,
  onClose,
}: {
  artists: Artist[];
  initialArtistId?: number;
  initialTag?: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [artistIds, setArtistIds] = useState<number[]>(initialArtistId ? [initialArtistId] : []);
  const [tags, setTags] = useState<string[]>(initialTag ? [initialTag] : []);
  const [title, setTitle] = useState("");
  const [showPrices, setShowPrices] = useState(true);
  const [onlyAvailable, setOnlyAvailable] = useState(false);
  const [artistSearch, setArtistSearch] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const { data: allTags = [] } = useQuery<string[]>({
    queryKey: ["share-tags"],
    queryFn: () => api.get("/shares/tags/").then((r) => r.data),
  });
  const { data: links = [] } = useQuery<ShareLink[]>({
    queryKey: ["shares"],
    queryFn: () => api.get("/shares/").then((r) => r.data),
  });

  const artistName = (id: number) => artists.find((a) => a.id === id)?.name_ru ?? `#${id}`;
  const autoTitle =
    [...artistIds.map(artistName), ...tags].join(", ") || (onlyAvailable ? "Работы в наличии" : "Каталог работ");

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["shares"] });
  const copy = async (link: ShareLink) => {
    if (await copyText(shareUrl(link.token))) {
      setCopiedId(link.id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const create = useMutation({
    mutationFn: () =>
      api
        .post<ShareLink>("/shares/", {
          title: title.trim() || autoTitle,
          artist_ids: artistIds,
          tags,
          only_available: onlyAvailable,
          show_prices: showPrices,
        })
        .then((r) => r.data),
    onSuccess: (link) => {
      setError("");
      setTitle("");
      invalidate();
      copy(link);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      setError(e.response?.data?.detail || "Не удалось создать ссылку"),
  });
  const toggle = useMutation({
    mutationFn: (link: ShareLink) => api.patch(`/shares/${link.id}/`, { is_active: !link.is_active }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/shares/${id}/`),
    onSuccess: invalidate,
  });

  const toggleIn = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const filteredArtists = artists.filter((a) =>
    a.name_ru.toLowerCase().includes(artistSearch.trim().toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center" onClick={onClose}>
      <div
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Ссылка на подборку</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>

        <label className="mb-1 block text-xs text-gray-500">Художники</label>
        {artistIds.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {artistIds.map((id) => (
              <button
                key={id}
                onClick={() => setArtistIds(toggleIn(artistIds, id))}
                className="flex items-center gap-1 rounded-full bg-gray-900 px-2.5 py-1 text-xs text-white"
              >
                {artistName(id)} <X size={12} />
              </button>
            ))}
          </div>
        )}
        <div className="relative mb-1">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={artistSearch}
            onChange={(e) => setArtistSearch(e.target.value)}
            placeholder="Найти художника"
            className="w-full rounded-lg border py-1.5 pl-8 pr-3 text-sm"
          />
        </div>
        <div className="mb-4 max-h-36 overflow-y-auto rounded-lg border">
          {filteredArtists.map((a) => (
            <label key={a.id} className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm hover:bg-gray-50">
              <input
                type="checkbox"
                checked={artistIds.includes(a.id)}
                onChange={() => setArtistIds(toggleIn(artistIds, a.id))}
              />
              {a.name_ru}
            </label>
          ))}
          {filteredArtists.length === 0 && <p className="px-3 py-2 text-sm text-gray-400">Не найдено</p>}
        </div>

        <label className="mb-1 block text-xs text-gray-500">Теги</label>
        <div className="mb-4 flex flex-wrap gap-1.5">
          {allTags.length === 0 && <span className="text-sm text-gray-400">Тегов пока нет</span>}
          {allTags.map((t) => (
            <button
              key={t}
              onClick={() => setTags(toggleIn(tags, t))}
              className={`rounded-full border px-2.5 py-1 text-xs ${
                tags.includes(t) ? "border-gray-900 bg-gray-900 text-white" : "text-gray-700 hover:bg-gray-50"
              }`}
            >
              #{t}
            </button>
          ))}
        </div>

        <label className="mb-1 block text-xs text-gray-500">Название (видит клиент)</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={autoTitle || "Например: Графика 1960-х"}
          maxLength={200}
          className="mb-3 w-full rounded-lg border px-3 py-2 text-sm"
        />
        <label className="mb-2 flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={onlyAvailable} onChange={(e) => setOnlyAvailable(e.target.checked)} />
          Только в наличии (статус «В продаже»)
        </label>
        <label className="mb-4 flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={showPrices} onChange={(e) => setShowPrices(e.target.checked)} />
          Показывать цены
        </label>
        <p className="mb-3 text-xs text-gray-500">
          {artistIds.length === 0 && tags.length === 0 && "Художник и теги не выбраны — по ссылке будет весь каталог. "}
          {onlyAvailable
            ? "Клиент увидит только работы в продаже."
            : "Клиент увидит работы в продаже, резерве, коллекции и на выставке."}{" "}
          Черновики и проданные скрыты, закупочная цена и место хранения не показываются.
        </p>
        {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
        <button
          onClick={() => create.mutate()}
          disabled={create.isPending}
          className="w-full rounded-lg bg-gray-900 py-2.5 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-40"
        >
          {create.isPending ? "Создаю…" : "Создать и скопировать ссылку"}
        </button>

        {links.length > 0 && (
          <div className="mt-6 border-t pt-4">
            <h3 className="mb-2 text-sm font-semibold text-gray-700">Созданные ссылки</h3>
            <ul className="space-y-2">
              {links.map((link) => (
                <li key={link.id} className={`rounded-lg border p-2.5 ${link.is_active ? "" : "opacity-50"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-900">{link.title}</p>
                      <p className="text-xs text-gray-500">
                        {worksLabel(link.artworks_count)}
                        {link.artist_ids.length === 0 && link.tags.length === 0 ? " · весь каталог" : ""}
                        {link.only_available ? " · в наличии" : ""}
                        {link.show_prices ? "" : " · без цен"}
                        {link.is_active ? "" : " · отключена"}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      <button onClick={() => copy(link)} title="Скопировать" className="rounded p-1.5 text-gray-500 hover:bg-gray-100">
                        {copiedId === link.id ? <Check size={15} className="text-green-600" /> : <Copy size={15} />}
                      </button>
                      <a href={`/s/${link.token}`} target="_blank" title="Открыть" className="rounded p-1.5 text-gray-500 hover:bg-gray-100">
                        <ExternalLink size={15} />
                      </a>
                      <button
                        onClick={() => {
                          if (confirm(`Удалить ссылку «${link.title}»? Она перестанет открываться.`)) remove.mutate(link.id);
                        }}
                        title="Удалить"
                        className="rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-red-600"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                  <button onClick={() => toggle.mutate(link)} className="mt-1 text-xs text-blue-600 hover:underline">
                    {link.is_active ? "Отключить" : "Включить"}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
