"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Upload, Sparkles, Loader2, Image as ImageIcon } from "lucide-react";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import type { ArtworkListItem } from "@/lib/types";

export default function CustomMockupPage() {
  const [roomFile, setRoomFile] = useState<File | null>(null);
  const [roomPreview, setRoomPreview] = useState<string | null>(null);
  const [selectedArtwork, setSelectedArtwork] = useState<number | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);

  const { data: artworks = [] } = useQuery<ArtworkListItem[]>({
    queryKey: ["artworks-for-mockup"],
    queryFn: () => api.get("/artworks", { params: { status: "for_sale", limit: 100 } }).then((r) => r.data),
  });

  const generate = useMutation({
    mutationFn: async () => {
      if (!roomFile || !selectedArtwork) throw new Error("Missing data");
      const fd = new FormData();
      fd.append("room_photo", roomFile);
      const { data } = await api.post(
        `/artworks/${selectedArtwork}/custom-mockup/`,
        fd,
        { responseType: "blob" }
      );
      return URL.createObjectURL(data as Blob);
    },
    onSuccess: (url) => setResultUrl(url),
  });

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-2 text-2xl font-bold text-gray-900">
        Персональный мокап
      </h1>
      <p className="mb-6 text-sm text-gray-500">
        Загрузите фото комнаты клиента, выберите произведение — AI покажет как оно будет смотреться
      </p>

      <div className="grid grid-cols-2 gap-6">
        {/* Шаг 1: Фото комнаты */}
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            1. Фото комнаты
          </h2>
          {roomPreview ? (
            <div className="relative">
              <img
                src={roomPreview}
                alt="Комната"
                className="w-full rounded-lg object-cover"
                style={{ maxHeight: 300 }}
              />
              <button
                onClick={() => {
                  setRoomFile(null);
                  setRoomPreview(null);
                  setResultUrl(null);
                }}
                className="absolute right-2 top-2 rounded-full bg-black/50 px-2 py-1 text-xs text-white hover:bg-black/70"
              >
                Заменить
              </button>
            </div>
          ) : (
            <label className="flex aspect-[4/3] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 hover:border-gray-400">
              <Upload size={32} className="mb-2 text-gray-400" />
              <span className="text-sm text-gray-500">Загрузить фото комнаты</span>
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    setRoomFile(file);
                    setRoomPreview(URL.createObjectURL(file));
                    setResultUrl(null);
                  }
                }}
              />
            </label>
          )}
        </div>

        {/* Шаг 2: Выбрать произведение */}
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            2. Выберите произведение
          </h2>
          <div className="max-h-[340px] space-y-2 overflow-y-auto">
            {artworks.map((aw) => (
              <button
                key={aw.id}
                onClick={() => {
                  setSelectedArtwork(aw.id);
                  setResultUrl(null);
                }}
                className={`flex w-full items-center gap-3 rounded-lg border p-2 text-left transition-colors ${
                  selectedArtwork === aw.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:bg-gray-50"
                }`}
              >
                {aw.primary_image ? (
                  <img
                    src={imageUrl(aw.primary_image)}
                    alt=""
                    className="h-12 w-12 rounded object-cover"
                  />
                ) : (
                  <div className="flex h-12 w-12 items-center justify-center rounded bg-gray-100">
                    <ImageIcon size={16} className="text-gray-400" />
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {aw.title || "Без названия"}
                  </p>
                  <p className="text-xs text-gray-500">{aw.artist.name_ru}</p>
                </div>
              </button>
            ))}
            {artworks.length === 0 && (
              <p className="py-8 text-center text-sm text-gray-400">
                Нет произведений в продаже
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Кнопка генерации */}
      <div className="mt-6 text-center">
        <button
          onClick={() => generate.mutate()}
          disabled={!roomFile || !selectedArtwork || generate.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-gray-900 px-8 py-3 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-40"
        >
          {generate.isPending ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Генерирую мокап...
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Сгенерировать мокап
            </>
          )}
        </button>
      </div>

      {/* Результат */}
      {resultUrl && (
        <div className="mt-6 rounded-xl bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Результат</h2>
          <img
            src={resultUrl}
            alt="Персональный мокап"
            className="w-full rounded-lg"
          />
          <div className="mt-3 flex gap-2">
            <a
              href={resultUrl}
              download="mockup.jpg"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
            >
              Скачать
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
