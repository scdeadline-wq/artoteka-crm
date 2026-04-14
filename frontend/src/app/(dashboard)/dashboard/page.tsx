"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";

export default function DashboardPage() {
  const { data, isLoading } = useQuery<DashboardSummary>({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/dashboard/summary").then((r) => r.data),
  });

  if (isLoading) return <p className="text-gray-500">Загрузка...</p>;
  if (!data) return null;

  const cards = [
    { label: "Выручка", value: `${data.total_revenue.toLocaleString("ru")} ₽` },
    { label: "Расходы на закупку", value: `${data.total_purchase.toLocaleString("ru")} ₽` },
    { label: "Маржа", value: `${data.margin.toLocaleString("ru")} ₽` },
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
    </div>
  );
}
