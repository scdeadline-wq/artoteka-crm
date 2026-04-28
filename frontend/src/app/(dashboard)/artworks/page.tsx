"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Plus, Search } from "lucide-react";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import type { ArtworkListItem, Artist, Technique } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  review: "bg-yellow-100 text-yellow-800",
  for_sale: "bg-green-100 text-green-800",
  reserved: "bg-blue-100 text-blue-800",
  sold: "bg-purple-100 text-purple-800",
  collection: "bg-orange-100 text-orange-800",
};

export default function ArtworksPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [artistFilter, setArtistFilter] = useState("");
  const [techniqueFilter, setTechniqueFilter] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");

  const { data: artists = [] } = useQuery<Artist[]>({
    queryKey: ["artists-for-filter"],
    queryFn: () => api.get("/artists").then((r) => r.data),
  });
  const { data: techniques = [] } = useQuery<Technique[]>({
    queryKey: ["techniques-for-filter"],
    queryFn: () => api.get("/techniques").then((r) => r.data),
  });

  const { data: artworks = [], isLoading } = useQuery<ArtworkListItem[]>({
    queryKey: ["artworks", search, statusFilter, artistFilter, techniqueFilter, yearFrom, yearTo],
    queryFn: () =>
      api
        .get("/artworks", {
          params: {
            q: search || undefined,
            status: statusFilter || undefined,
            artist_id: artistFilter || undefined,
            technique_id: techniqueFilter || undefined,
            year_from: yearFrom || undefined,
            year_to: yearTo || undefined,
          },
        })
        .then((r) => r.data),
  });

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("");
    setArtistFilter("");
    setTechniqueFilter("");
    setYearFrom("");
    setYearTo("");
  };
  const filtersActive =
    !!search || !!statusFilter || !!artistFilter || !!techniqueFilter || !!yearFrom || !!yearTo;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Произведения</h1>
        <Link
          href="/artworks/new"
          className="flex items-center gap-2 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          <Plus size={16} />
          Добавить
        </Link>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            placeholder="Поиск по названию..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border py-2 pl-9 pr-4 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="">Все статусы</option>
          {Object.entries(STATUS_LABELS).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={artistFilter}
          onChange={(e) => setArtistFilter(e.target.value)}
          className="max-w-[200px] rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="">Все художники</option>
          {artists.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name_ru}
            </option>
          ))}
        </select>
        <select
          value={techniqueFilter}
          onChange={(e) => setTechniqueFilter(e.target.value)}
          className="max-w-[200px] rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="">Все техники</option>
          {techniques.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Год от"
          value={yearFrom}
          onChange={(e) => setYearFrom(e.target.value)}
          className="w-24 rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <input
          type="number"
          placeholder="до"
          value={yearTo}
          onChange={(e) => setYearTo(e.target.value)}
          className="w-20 rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        {filtersActive && (
          <button
            onClick={resetFilters}
            className="rounded-lg border px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Сбросить
          </button>
        )}
      </div>

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : artworks.length === 0 ? (
        <p className="text-gray-500">Нет произведений</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {artworks.map((aw) => (
            <Link
              key={aw.id}
              href={`/artworks/${aw.id}`}
              className="group overflow-hidden rounded-xl bg-white shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="aspect-[4/3] bg-gray-100">
                {aw.primary_image ? (
                  <img
                    src={imageUrl(aw.primary_image)}
                    alt={aw.title || ""}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-gray-300">
                    Нет фото
                  </div>
                )}
              </div>
              <div className="p-4">
                <p className="text-sm font-medium text-gray-900 group-hover:text-blue-600">
                  {aw.title || "Без названия"}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">
                  {aw.artist.name_ru}
                  {aw.year ? `, ${aw.year}` : ""}
                </p>
                <div className="mt-2 flex items-center justify-between">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[aw.status] || ""}`}
                  >
                    {STATUS_LABELS[aw.status] || aw.status}
                  </span>
                  {aw.sale_price && (
                    <span className="text-sm font-semibold text-gray-900">
                      {aw.sale_price.toLocaleString("ru")} ₽
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-400">
                  #{aw.inventory_number}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
