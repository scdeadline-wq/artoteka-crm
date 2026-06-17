"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { Star, Send, Trash2, Plus, Search, X } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import { useDebounced } from "@/lib/use-debounced";
import { formatPrice } from "@/lib/currency";
import type { SelectionItem, ArtworkListItem } from "@/lib/types";

// Подборка работ под клиента: ⭐ предложить / 📤 отправлено на просмотр.
export default function ClientSelectionBlock({ clientId }: { clientId: number }) {
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [search, setSearch] = useState("");
  const debounced = useDebounced(search);

  const { data: items = [] } = useQuery<SelectionItem[]>({
    queryKey: ["selection", clientId],
    queryFn: () => api.get(`/clients/${clientId}/selection/`).then((r) => r.data),
  });

  const { data: searchResults = [] } = useQuery<ArtworkListItem[]>({
    queryKey: ["selection-search", debounced],
    queryFn: () => api.get("/artworks", { params: { q: debounced, limit: 8 } }).then((r) => r.data),
    enabled: adding && debounced.length > 0,
    placeholderData: keepPreviousData,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["selection", clientId] });

  const add = useMutation({
    mutationFn: (artwork_id: number) =>
      api.post(`/clients/${clientId}/selection/`, { artwork_id, status: "shortlist" }),
    onSuccess: invalidate,
  });
  const setStatus = useMutation({
    mutationFn: ({ artwork_id, status }: { artwork_id: number; status: string }) =>
      api.patch(`/clients/${clientId}/selection/${artwork_id}/`, { status }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (artwork_id: number) => api.delete(`/clients/${clientId}/selection/${artwork_id}/`),
    onSuccess: invalidate,
  });

  const chosenIds = new Set(items.map((i) => i.artwork_id));

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Подборка работ</h3>
        <button
          onClick={() => setAdding((v) => !v)}
          className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
        >
          {adding ? <X size={13} /> : <Plus size={13} />}
          {adding ? "Закрыть" : "Добавить работу"}
        </button>
      </div>

      {adding && (
        <div className="mb-3 rounded-lg border bg-gray-50 p-2">
          <div className="relative mb-2">
            <Search size={14} className="absolute left-2 top-2.5 text-gray-400" />
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск работы по № или названию"
              className="w-full rounded-lg border py-2 pl-7 pr-3 text-sm"
            />
          </div>
          {searchResults.length > 0 && (
            <ul className="max-h-48 space-y-1 overflow-y-auto">
              {searchResults.map((a) => (
                <li key={a.id} className="flex items-center gap-2 rounded px-1 py-1 hover:bg-white">
                  {a.primary_image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={imageUrl(a.primary_image)} alt="" className="h-8 w-8 rounded object-cover" />
                  ) : (
                    <div className="h-8 w-8 rounded bg-gray-200" />
                  )}
                  <span className="flex-1 truncate text-xs">
                    #{a.inventory_number} {a.title || ""}
                    <span className="text-gray-400"> — {a.artist?.name_ru}</span>
                  </span>
                  <button
                    onClick={() => add.mutate(a.id)}
                    disabled={chosenIds.has(a.id)}
                    className="rounded bg-gray-900 px-2 py-1 text-xs text-white disabled:opacity-30"
                  >
                    {chosenIds.has(a.id) ? "✓" : "+"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {items.length === 0 ? (
        <p className="text-xs text-gray-400">Пусто. Добавь работы, чтобы предложить клиенту.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <li key={it.artwork_id} className="flex items-center gap-2 text-sm">
              {it.primary_image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={imageUrl(it.primary_image)} alt="" className="h-9 w-9 rounded object-cover" />
              ) : (
                <div className="h-9 w-9 rounded bg-gray-200" />
              )}
              <Link href={`/artworks/${it.artwork_id}`} className="flex-1 truncate text-gray-700 hover:text-blue-600 hover:underline">
                #{it.inventory_number} {it.artwork_title || "Без названия"}
                {it.sale_price ? <span className="text-gray-400"> · {formatPrice(it.sale_price, it.currency)}</span> : null}
              </Link>
              <button
                title="Предложить (в подборке)"
                onClick={() => setStatus.mutate({ artwork_id: it.artwork_id, status: "shortlist" })}
                className={it.status === "shortlist" ? "text-amber-500" : "text-gray-300 hover:text-amber-400"}
              >
                <Star size={16} fill={it.status === "shortlist" ? "currentColor" : "none"} />
              </button>
              <button
                title="Отправлено на просмотр"
                onClick={() => setStatus.mutate({ artwork_id: it.artwork_id, status: "sent" })}
                className={it.status === "sent" ? "text-green-600" : "text-gray-300 hover:text-green-500"}
              >
                <Send size={15} />
              </button>
              <button
                title="Убрать из подборки"
                onClick={() => remove.mutate(it.artwork_id)}
                className="text-gray-300 hover:text-red-600"
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
