"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Sale } from "@/lib/types";

export default function SalesPage() {
  const { data: sales = [] } = useQuery<Sale[]>({
    queryKey: ["sales"],
    queryFn: () => api.get("/sales").then((r) => r.data),
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Продажи</h1>
      <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-gray-500">
              <th className="px-4 py-3">Дата</th>
              <th className="px-4 py-3">Работа</th>
              <th className="px-4 py-3">Художник</th>
              <th className="px-4 py-3">Покупатель</th>
              <th className="px-4 py-3">Реферал</th>
              <th className="px-4 py-3 text-right">Продажа</th>
              <th className="px-4 py-3 text-right">Закупка</th>
              <th className="px-4 py-3 text-right">Маржа</th>
            </tr>
          </thead>
          <tbody>
            {sales.map((s) => (
              <tr key={s.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">
                  {new Date(s.sold_at).toLocaleDateString("ru")}
                </td>
                <td className="px-4 py-3 font-medium text-gray-900">
                  {s.artwork_title || "—"}
                </td>
                <td className="px-4 py-3 text-gray-600">{s.artist_name || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{s.client_name}</td>
                <td className="px-4 py-3 text-gray-500">{s.referral_name || "—"}</td>
                <td className="px-4 py-3 text-right font-medium">
                  {s.sold_price.toLocaleString("ru")} ₽
                </td>
                <td className="px-4 py-3 text-right text-gray-500">
                  {s.purchase_price ? `${s.purchase_price.toLocaleString("ru")} ₽` : "—"}
                </td>
                <td
                  className={`px-4 py-3 text-right font-semibold ${
                    s.margin && s.margin > 0 ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {s.margin != null ? `${s.margin.toLocaleString("ru")} ₽` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
