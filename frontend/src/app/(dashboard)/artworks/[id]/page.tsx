"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import type { Artwork } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";
import ArtworkMockup from "@/components/mockup";

export default function ArtworkDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const { data: artwork, isLoading } = useQuery<Artwork>({
    queryKey: ["artwork", id],
    queryFn: () => api.get(`/artworks/${id}`).then((r) => r.data),
  });

  if (isLoading) return <p className="text-gray-500">Загрузка...</p>;
  if (!artwork) return <p className="text-red-500">Не найдено</p>;

  const primaryImage = artwork.images.find((i) => i.is_primary) || artwork.images[0];

  return (
    <div className="mx-auto max-w-4xl">
      <Link
        href="/artworks"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"
      >
        <ArrowLeft size={16} /> Назад
      </Link>

      {/* Верхний блок: фото + инфо */}
      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {artwork.title || "Без названия"}
            </h1>
            <p className="mt-1 text-gray-600">
              {artwork.artist.name_ru}
              {artwork.artist.name_en ? ` (${artwork.artist.name_en})` : ""}
              {artwork.year ? `, ${artwork.year}` : ""}
            </p>
          </div>
          <span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium">
            {STATUS_LABELS[artwork.status] || artwork.status}
          </span>
        </div>

        {artwork.images.length > 0 && (
          <div className="mb-6 flex gap-3 overflow-x-auto">
            {artwork.images.map((img) => (
              <img
                key={img.id}
                src={imageUrl(img.url)}
                alt=""
                className="h-56 rounded-lg object-cover"
              />
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
          <div>
            <p className="text-gray-500">Инвентарный номер</p>
            <p className="font-medium">#{artwork.inventory_number}</p>
          </div>
          {artwork.techniques.length > 0 && (
            <div className="col-span-2">
              <p className="text-gray-500">Техника</p>
              <p className="font-medium">
                {artwork.techniques.map((t) => t.name).join(", ")}
              </p>
            </div>
          )}
          <div>
            <p className="text-gray-500">Экспертиза</p>
            <p className="font-medium">{artwork.has_expertise ? "Есть" : "Нет"}</p>
          </div>
          {artwork.edition && (
            <div>
              <p className="text-gray-500">Тираж</p>
              <p className="font-medium">{artwork.edition}</p>
            </div>
          )}
          {artwork.location && (
            <div>
              <p className="text-gray-500">Местоположение</p>
              <p className="font-medium">{artwork.location}</p>
            </div>
          )}
          {artwork.purchase_price != null && (
            <div>
              <p className="text-gray-500">Цена закупки</p>
              <p className="font-medium">
                {artwork.purchase_price.toLocaleString("ru")} ₽
              </p>
            </div>
          )}
          {artwork.sale_price != null && (
            <div>
              <p className="text-gray-500">Цена продажи</p>
              <p className="font-semibold text-green-700">
                {artwork.sale_price.toLocaleString("ru")} ₽
              </p>
            </div>
          )}
          {artwork.condition && (
            <div>
              <p className="text-gray-500">Состояние</p>
              <p className="font-medium">{artwork.condition}</p>
            </div>
          )}
        </div>

        {artwork.description && (
          <div className="mt-4 border-t pt-4">
            <p className="mb-1 text-sm text-gray-500">Описание</p>
            <p className="text-sm leading-relaxed text-gray-700">
              {artwork.description}
            </p>
          </div>
        )}
      </div>

      {/* Мокапы в интерьере */}
      {primaryImage && (
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            В интерьере
          </h2>
          <ArtworkMockup
            imageSrc={primaryImage.url}
            title={artwork.title || undefined}
          />
        </div>
      )}
    </div>
  );
}
