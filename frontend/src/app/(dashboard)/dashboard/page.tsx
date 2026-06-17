"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { DashboardSummary, Sale } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";
import { formatPrice } from "@/lib/currency";

interface TopArtist {
  artist_id: number;
  name: string;
  sales_count: number;
  total_revenue: number;
  currency: string;
}

// {USD: 25000, RUB: 80000} → "25 000 $ · 80 000 ₽"
function joinByCurrency(map: Record<string, number> | undefined): string {
  if (!map || Object.keys(map).length === 0) return "—";
  return Object.entries(map)
    .filter(([, v]) => v)
    .map(([code, v]) => formatPrice(v, code))
    .join(" · ") || "—";
}

function plural(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return "продажа";
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return "продажи";
  return "продаж";
}

export default function DashboardPage() {
  const [tab, setTab] = useState<"recent" | "artists">("recent");

  const { data, isLoading } = useQuery<DashboardSummary>({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/dashboard/summary").then((r) => r.data),
  });

  const { data: recentSales = [] } = useQuery<Sale[]>({
    queryKey: ["dashboard-recent-sales"],
    queryFn: () => api.get("/dashboard/recent-sales/").then((r) => r.data),
  });

  const { data: topArtists = [] } = useQuery<TopArtist[]>({
    queryKey: ["dashboard-top-artists"],
    queryFn: () => api.get("/dashboard/top-artists/").then((r) => r.data),
  });

  if (isLoading) return <p className="text-gray-500">Загрузка...</p>;
  if (!data) return null;

  const cards = [
    { label: "Выручка", value: joinByCurrency(data.revenue_by_currency) },
    ...(data.purchase_by_currency != null
      ? [{ label: "Расходы на закупку", value: joinByCurrency(data.purchase_by_currency) }]
      : []),
    ...(data.margin_by_currency != null
      ? [{ label: "Маржа", value: joinByCurrency(data.margin_by_currency) }]
      : []),
    { label: "Продаж", value: String(data.total_sales) },
    { label: "Реферальные", value: joinByCurrency(data.referral_by_currency) },
  ];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Дашборд</h1>

      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-5">
        {cards.map((c) => (
          <div key={c.label} className="rounded-xl bg-white p-4 shadow-sm">
            <p className="text-xs text-gray-500">{c.label}</p>
            <p className="mt-1 text-xl font-semibold text-gray-900">{c.value}</p>
          </div>
        ))}
      </div>

      <div className="mb-6 rounded-xl bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Работы по статусам</h2>
        <div className="flex flex-wrap gap-3">
          {Object.entries(data.artworks_by_status).map(([status, count]) => (
            <div key={status} className="rounded-lg bg-gray-50 px-4 py-2 text-sm">
              <span className="text-gray-500">{STATUS_LABELS[status] || status}</span>{" "}
              <span className="font-semibold text-gray-900">{count}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl bg-white p-5 shadow-sm">
        <div className="mb-4 flex gap-2 border-b">
          <button
            onClick={() => setTab("recent")}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              tab === "recent"
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-400 hover:text-gray-600"
            }`}
          >
            Последние сделки
          </button>
          <button
            onClick={() => setTab("artists")}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              tab === "artists"
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-400 hover:text-gray-600"
            }`}
          >
            Топ художников
          </button>
        </div>

        {tab === "recent" ? (
          recentSales.length === 0 ? (
            <p className="py-3 text-sm text-gray-400">Продаж пока нет</p>
          ) : (
            <ul className="divide-y">
              {recentSales.map((s) => (
                <li key={s.id} className="flex items-center gap-3 py-2 text-sm">
                  <span className="text-xs text-gray-400">
                    {new Date(s.sold_at).toLocaleDateString("ru")}
                  </span>
                  <Link
                    href={`/artworks/${s.artwork_id}`}
                    className="flex-1 truncate font-medium text-gray-900 hover:underline"
                  >
                    {s.artwork_title || `#${s.artwork_id}`}
                    {s.artist_name ? <span className="text-gray-400"> — {s.artist_name}</span> : null}
                  </Link>
                  <span className="hidden truncate text-xs text-gray-500 sm:block">{s.client_name}</span>
                  <span className="whitespace-nowrap font-semibold text-gray-900">
                    {formatPrice(s.sold_price, s.currency)}
                  </span>
                </li>
              ))}
            </ul>
          )
        ) : topArtists.length === 0 ? (
          <p className="py-3 text-sm text-gray-400">Нет данных</p>
        ) : (
          <ul className="divide-y">
            {topArtists.map((a, i) => (
              <li key={`${a.artist_id}-${a.currency}`} className="flex items-center gap-3 py-2 text-sm">
                <span className="w-5 text-right text-gray-400">{i + 1}.</span>
                <span className="flex-1 font-medium text-gray-900">{a.name}</span>
                <span className="text-xs text-gray-500">
                  {a.sales_count} {plural(a.sales_count)}
                </span>
                <span className="whitespace-nowrap font-semibold text-gray-900">
                  {formatPrice(a.total_revenue, a.currency)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
