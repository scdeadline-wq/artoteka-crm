"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import api from "@/lib/api";
import type { Sale } from "@/lib/types";

export default function SalesPage() {
  const { data: sales = [] } = useQuery<Sale[]>({
    queryKey: ["sales"],
    queryFn: () => api.get("/sales").then((r) => r.data),
  });

  const totalRevenue = sales.reduce((s, x) => s + Number(x.sold_price), 0);
  const totalMargin = sales.reduce((s, x) => s + (x.margin ? Number(x.margin) : 0), 0);

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold text-gray-900">Продажи</h1>

      {sales.length > 0 && (
        <div className="mb-4 flex gap-4">
          <div className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <p className="text-xs text-gray-500">Всего продаж</p>
            <p className="text-lg font-bold">{sales.length}</p>
          </div>
          <div className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <p className="text-xs text-gray-500">Выручка</p>
            <p className="text-lg font-bold">{totalRevenue.toLocaleString("ru")} ₽</p>
          </div>
          <div className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <p className="text-xs text-gray-500">Маржа</p>
            <p className={`text-lg font-bold ${totalMargin >= 0 ? "text-green-600" : "text-red-600"}`}>
              {totalMargin.toLocaleString("ru")} ₽
            </p>
          </div>
        </div>
      )}

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
                <td className="px-4 py-3">
                  <Link href={`/artworks/${s.artwork_id}`} className="font-medium text-blue-600 hover:underline">
                    {s.artwork_title || `#${s.artwork_id}`}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-600">{s.artist_name || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{s.client_name}</td>
                <td className="px-4 py-3 text-gray-500">{s.referral_name || "—"}</td>
                <td className="px-4 py-3 text-right font-medium">
                  {Number(s.sold_price).toLocaleString("ru")} ₽
                </td>
                <td className="px-4 py-3 text-right text-gray-500">
                  {s.purchase_price ? `${Number(s.purchase_price).toLocaleString("ru")} ₽` : "—"}
                </td>
                <td className={`px-4 py-3 text-right font-semibold ${
                  s.margin && Number(s.margin) > 0 ? "text-green-600" : s.margin ? "text-red-600" : ""
                }`}>
                  {s.margin != null ? `${Number(s.margin).toLocaleString("ru")} ₽` : "—"}
                </td>
              </tr>
            ))}
            {sales.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Нет продаж</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
