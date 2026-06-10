"use client";

import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Download } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { useAuthStore, isAdmin as isAdminRole } from "@/lib/store";
import type { Sale } from "@/lib/types";

export default function SalesPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = isAdminRole(user);

  // Фильтр за период (пусто = всё время)
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [exporting, setExporting] = useState(false);

  const { data: sales = [] } = useQuery<Sale[]>({
    queryKey: ["sales", dateFrom, dateTo],
    queryFn: () =>
      api
        .get("/sales", {
          params: { date_from: dateFrom || undefined, date_to: dateTo || undefined },
        })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
  });

  // Тоталы считаются по отфильтрованному набору (сервер уже отдаёт за период)
  const totalRevenue = sales.reduce((s, x) => s + Number(x.sold_price), 0);
  const totalMargin = sales.reduce((s, x) => s + (x.margin ? Number(x.margin) : 0), 0);

  async function exportCsv() {
    setExporting(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const params = new URLSearchParams();
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      const qs = params.toString();
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const res = await fetch(`${base}/sales/export/${qs ? `?${qs}` : ""}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const period = [dateFrom, dateTo].filter(Boolean).join("_");
      a.download = `sales_${period || "all"}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      alert("Не удалось выгрузить CSV");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold text-gray-900">Продажи</h1>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="mb-1 block text-xs text-gray-500">С</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">По</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        {(dateFrom || dateTo) && (
          <button
            onClick={() => { setDateFrom(""); setDateTo(""); }}
            className="rounded-lg border px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Сбросить
          </button>
        )}
        <button
          onClick={exportCsv}
          disabled={exporting}
          className="ml-auto flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          <Download size={14} /> {exporting ? "Выгружаю..." : "Экспорт CSV"}
        </button>
      </div>

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
          {isAdmin && (
            <div className="rounded-xl bg-white px-4 py-3 shadow-sm">
              <p className="text-xs text-gray-500">Маржа</p>
              <p className={`text-lg font-bold ${totalMargin >= 0 ? "text-green-600" : "text-red-600"}`}>
                {totalMargin.toLocaleString("ru")} ₽
              </p>
            </div>
          )}
        </div>
      )}

      <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-gray-500">
              <th className="px-4 py-3">Дата</th>
              <th className="px-4 py-3">Работа</th>
              <th className="px-4 py-3">Художник</th>
              <th className="px-4 py-3">Покупатель</th>
              <th className="px-4 py-3">Реферал</th>
              <th className="px-4 py-3 text-right">Продажа</th>
              {isAdmin && <th className="px-4 py-3 text-right">Закупка</th>}
              {isAdmin && <th className="px-4 py-3 text-right">Маржа</th>}
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
                {isAdmin && (
                  <td className="px-4 py-3 text-right text-gray-500">
                    {s.purchase_price ? `${Number(s.purchase_price).toLocaleString("ru")} ₽` : "—"}
                  </td>
                )}
                {isAdmin && (
                  <td className={`px-4 py-3 text-right font-semibold ${
                    s.margin && Number(s.margin) > 0 ? "text-green-600" : s.margin ? "text-red-600" : ""
                  }`}>
                    {s.margin != null ? `${Number(s.margin).toLocaleString("ru")} ₽` : "—"}
                  </td>
                )}
              </tr>
            ))}
            {sales.length === 0 && (
              <tr><td colSpan={isAdmin ? 8 : 6} className="px-4 py-8 text-center text-gray-400">Нет продаж</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
