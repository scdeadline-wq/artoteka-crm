"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Client } from "@/lib/types";
import { CLIENT_TYPE_LABELS } from "@/lib/types";

export default function ClientsPage() {
  const { data: clients = [] } = useQuery<Client[]>({
    queryKey: ["clients"],
    queryFn: () => api.get("/clients").then((r) => r.data),
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Клиенты</h1>
      <div className="rounded-xl bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-gray-500">
              <th className="px-4 py-3">Имя</th>
              <th className="px-4 py-3">Тип</th>
              <th className="px-4 py-3">Телефон</th>
              <th className="px-4 py-3">Telegram</th>
              <th className="px-4 py-3">Предпочтения</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{c.name}</td>
                <td className="px-4 py-3 text-gray-600">
                  {CLIENT_TYPE_LABELS[c.client_type] || c.client_type}
                </td>
                <td className="px-4 py-3 text-gray-600">{c.phone || "—"}</td>
                <td className="px-4 py-3 text-gray-600">{c.telegram || "—"}</td>
                <td className="px-4 py-3 text-gray-500">
                  {c.preferred_artists.map((a) => a.name_ru).join(", ") || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
