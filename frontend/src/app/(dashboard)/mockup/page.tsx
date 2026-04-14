"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, Sparkles, Loader2, Image as ImageIcon, Download, Clock } from "lucide-react";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import type { ArtworkListItem } from "@/lib/types";

interface MockupHistoryItem {
  id: number;
  artwork_id: number;
  artwork_title: string | null;
  artist_name: string | null;
  room_url: string;
  result_url: string;
  created_at: string;
}

export default function CustomMockupPage() {
  const queryClient = useQueryClient();
  const [roomFile, setRoomFile] = useState<File | null>(null);
  const [roomPreview, setRoomPreview] = useState<string | null>(null);
  const [selectedArtwork, setSelectedArtwork] = useState<number | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);

  const { data: artworks = [] } = useQuery<ArtworkListItem[]>({
    queryKey: ["artworks-for-mockup"],
    queryFn: () => api.get("/artworks", { params: { limit: 100 } }).then((r) => r.data),
  });

  const { data: history = [] } = useQuery<MockupHistoryItem[]>({
    queryKey: ["mockup-history"],
    queryFn: () => api.get("/artworks/mockups/history").then((r) => r.data),
  });

  const generate = useMutation({
    mutationFn: async () => {
      if (!roomFile || !selectedArtwork) throw new Error("Missing data");
      const fd = new FormData();
      fd.append("room_photo", roomFile);
      const { data } = await api.post(`/artworks/${selectedArtwork}/custom-mockup/`, fd);
      return data as { id: number; result_url: string };
    },
    onSuccess: (data) => {
      setResultUrl(imageUrl(data.result_url));
      queryClient.invalidateQueries({ queryKey: ["mockup-history"] });
    },
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
                Нет произведений
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
          <div className="mt-3">
            <a
              href={resultUrl}
              download="mockup.jpg"
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
            >
              <Download size={14} /> Скачать
            </a>
          </div>
        </div>
      )}

      {/* История мокапов */}
      {history.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
            <Clock size={18} /> История мокапов
          </h2>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            {history.map((m) => (
              <div key={m.id} className="group overflow-hidden rounded-xl bg-white shadow-sm">
                <a href={imageUrl(m.result_url)} target="_blank" rel="noreferrer">
                  <img
                    src={imageUrl(m.result_url)}
                    alt=""
                    className="aspect-[4/3] w-full object-cover transition-transform group-hover:scale-105"
                  />
                </a>
                <div className="p-3">
                  <p className="text-sm font-medium text-gray-900">
                    {m.artwork_title || "Без названия"}
                  </p>
                  <p className="text-xs text-gray-500">
                    {m.artist_name} — {new Date(m.created_at).toLocaleDateString("ru")}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
