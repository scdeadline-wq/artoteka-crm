"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";

interface TopArtist {
  artist_id: number;
  name: string;
  sales_count: number;
  total_revenue: number;
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery<DashboardSummary>({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/dashboard/summary").then((r) => r.data),
  });

  const { data: topArtists = [] } = useQuery<TopArtist[]>({
    queryKey: ["dashboard-top-artists"],
    queryFn: () => api.get("/dashboard/top-artists/").then((r) => r.data),
  });

  if (isLoading) return <p className="text-gray-500">Загрузка...</p>;
  if (!data) return null;

  const cards = [
    { label: "Выручка", value: `${data.total_revenue.toLocaleString("ru")} ₽` },
    ...(data.total_purchase != null
      ? [{ label: "Расходы на закупку", value: `${data.total_purchase.toLocaleString("ru")} ₽` }]
      : []),
    ...(data.margin != null
      ? [{ label: "Маржа", value: `${data.margin.toLocaleString("ru")} ₽` }]
      : []),
    { label: "Продаж", value: data.total_sales },
    { label: "Реферальные", value: `${data.total_referral_fees.toLocaleString("ru")} ₽` },
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

      <div className="rounded-xl bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">
          Работы по статусам
        </h2>
        <div className="flex flex-wrap gap-3">
          {Object.entries(data.artworks_by_status).map(([status, count]) => (
            <div
              key={status}
              className="rounded-lg bg-gray-50 px-4 py-2 text-sm"
            >
              <span className="text-gray-500">
                {STATUS_LABELS[status] || status}
              </span>{" "}
              <span className="font-semibold text-gray-900">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {topArtists.length > 0 && (
        <div className="mt-6 rounded-xl bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            Топ художников
          </h2>
          <ul className="divide-y">
            {topArtists.map((a, i) => (
              <li key={a.artist_id} className="flex items-center gap-3 py-2 text-sm">
                <span className="w-5 text-right text-gray-400">{i + 1}.</span>
                <span className="flex-1 font-medium text-gray-900">{a.name}</span>
                <span className="text-xs text-gray-500">
                  {a.sales_count}{" "}
                  {a.sales_count % 10 === 1 && a.sales_count % 100 !== 11
                    ? "продажа"
                    : [2, 3, 4].includes(a.sales_count % 10) && ![12, 13, 14].includes(a.sales_count % 100)
                    ? "продажи"
                    : "продаж"}
                </span>
                <span className="whitespace-nowrap font-semibold text-gray-900">
                  {a.total_revenue.toLocaleString("ru")} ₽
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
