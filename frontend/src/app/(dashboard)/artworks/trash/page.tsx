"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RotateCcw } from "lucide-react";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import { useAuthStore, isAdmin as isAdminRole } from "@/lib/store";
import { useEffect } from "react";

interface TrashedArtwork {
  id: number;
  inventory_number: number;
  title: string | null;
  artist: { id: number; name_ru: string; name_en: string | null };
  status: string;
  sale_price: number | null;
  primary_image: string | null;
  year: number | null;
  room: { id: number; name: string; sort_order: number } | null;
  deleted_at: string | null;
}

export default function TrashPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const canAccess = isAdminRole(user);

  useEffect(() => {
    if (user && !canAccess) router.replace("/artworks");
  }, [user, canAccess, router]);

  const { data: items = [], isLoading } = useQuery<TrashedArtwork[]>({
    queryKey: ["artworks-trash"],
    queryFn: () => api.get("/artworks/trash/").then((r) => r.data),
    enabled: canAccess,
  });

  const restoreMutation = useMutation({
    mutationFn: (id: number) => api.post(`/artworks/${id}/restore`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artworks-trash"] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
    },
  });

  if (!canAccess) return null;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-4 flex items-center justify-between">
        <Link
          href="/artworks"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft size={16} /> К списку работ
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">Корзина</h1>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : items.length === 0 ? (
        <p className="text-gray-500">Корзина пуста.</p>
      ) : (
        <div className="space-y-3">
          {items.map((aw) => (
            <div
              key={aw.id}
              className="flex items-center gap-4 rounded-xl bg-white p-4 shadow-sm"
            >
              <div className="h-20 w-20 flex-shrink-0 overflow-hidden rounded-lg bg-gray-100">
                {aw.primary_image ? (
                  <img
                    src={imageUrl(aw.primary_image)}
                    alt={aw.title || ""}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-gray-300">
                    Нет фото
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {aw.artist.name_ru} — {aw.title || "Без названия"}
                </p>
                <p className="text-xs text-gray-500">
                  №{aw.inventory_number}
                  {aw.room ? ` · Комната: ${aw.room.name}` : ""}
                  {aw.year ? ` · ${aw.year}` : ""}
                </p>
                {aw.deleted_at && (
                  <p className="mt-0.5 text-xs text-gray-400">
                    Удалена: {new Date(aw.deleted_at).toLocaleString("ru")}
                  </p>
                )}
              </div>
              <button
                onClick={() => restoreMutation.mutate(aw.id)}
                disabled={restoreMutation.isPending}
                className="flex items-center gap-1.5 rounded-lg border border-blue-300 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-50 disabled:opacity-50"
              >
                <RotateCcw size={14} /> Восстановить
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
