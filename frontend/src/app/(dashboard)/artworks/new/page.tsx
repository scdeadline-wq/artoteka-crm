"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Upload, Sparkles, Loader2, X, Check } from "lucide-react";
import api from "@/lib/api";
import type { Artist, Technique } from "@/lib/types";

type Step = "upload" | "review";

interface AISuggestion {
  title: string | null;
  artist: { id: number; name_ru: string; name_en: string | null } | null;
  artist_name_suggestion: string | null;
  year: number | null;
  techniques: { id: number; name: string }[];
  description: string | null;
  condition: string | null;
  style_period: string | null;
  estimated_price_rub: string | null;
  confidence: string | null;
}

export default function NewArtworkPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("upload");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [aiSuggestion, setAiSuggestion] = useState<AISuggestion | null>(null);

  const { data: artists = [] } = useQuery<Artist[]>({
    queryKey: ["artists"],
    queryFn: () => api.get("/artists").then((r) => r.data),
  });
  const { data: techniques = [] } = useQuery<Technique[]>({
    queryKey: ["techniques"],
    queryFn: () => api.get("/techniques").then((r) => r.data),
  });

  const [form, setForm] = useState({
    title: "",
    artist_id: 0,
    new_artist_name: "",
    year: "",
    edition: "",
    description: "",
    condition: "",
    location: "",
    purchase_price: "",
    sale_price: "",
    status: "draft",
    technique_ids: [] as number[],
  });

  // AI анализ
  const analyze = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/artworks/analyze-image", fd);
      return data.suggested as AISuggestion;
    },
    onSuccess: (suggestion) => {
      setAiSuggestion(suggestion);
      // Автозаполнение формы из AI
      setForm((f) => ({
        ...f,
        title: suggestion.title || "",
        artist_id: suggestion.artist?.id || 0,
        new_artist_name:
          !suggestion.artist && suggestion.artist_name_suggestion
            ? suggestion.artist_name_suggestion
            : "",
        year: suggestion.year ? String(suggestion.year) : "",
        description: suggestion.description || "",
        condition: suggestion.condition || "",
        technique_ids: suggestion.techniques.map((t) => t.id),
        sale_price: suggestion.estimated_price_rub
          ? String(suggestion.estimated_price_rub)
          : "",
      }));
      setStep("review");
    },
  });

  // Создание работы
  const create = useMutation({
    mutationFn: async () => {
      // Если новый художник — создадим его сначала
      let artistId = form.artist_id;
      if (!artistId && form.new_artist_name) {
        const { data: newArtist } = await api.post("/artists", {
          name_ru: form.new_artist_name,
        });
        artistId = newArtist.id;
      }

      const { data: artwork } = await api.post("/artworks", {
        title: form.title || null,
        artist_id: artistId,
        year: form.year ? Number(form.year) : null,
        edition: form.edition || null,
        description: form.description || null,
        condition: form.condition || null,
        location: form.location || null,
        purchase_price: form.purchase_price ? Number(form.purchase_price) : null,
        sale_price: form.sale_price ? Number(form.sale_price) : null,
        status: form.status,
        technique_ids: form.technique_ids,
      });

      // Загружаем фото
      if (imageFile) {
        const fd = new FormData();
        fd.append("file", imageFile);
        await api.post(`/artworks/${artwork.id}/images?is_primary=true`, fd);
      }

      return artwork;
    },
    onSuccess: () => router.push("/artworks"),
  });

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file?.type.startsWith("image/")) {
        handleFile(file);
      }
    },
    []
  );

  function handleFile(file: File) {
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    analyze.mutate(file);
  }

  function toggleTechnique(id: number) {
    setForm((f) => ({
      ...f,
      technique_ids: f.technique_ids.includes(id)
        ? f.technique_ids.filter((t) => t !== id)
        : [...f.technique_ids, id],
    }));
  }

  const grouped = techniques.reduce<Record<string, Technique[]>>((acc, t) => {
    const cat = t.category || "Прочее";
    (acc[cat] = acc[cat] || []).push(t);
    return acc;
  }, {});

  // === Шаг 1: Загрузка фото ===
  if (step === "upload") {
    return (
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-6 text-2xl font-bold text-gray-900">
          Новое произведение
        </h1>

        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="rounded-xl border-2 border-dashed border-gray-300 bg-white p-12 text-center transition-colors hover:border-gray-400"
        >
          {analyze.isPending ? (
            <div className="flex flex-col items-center gap-4">
              {imagePreview && (
                <img
                  src={imagePreview}
                  alt=""
                  className="mx-auto h-48 rounded-lg object-contain"
                />
              )}
              <div className="flex items-center gap-3">
                <Loader2 size={24} className="animate-spin text-blue-600" />
                <div>
                  <p className="font-medium text-gray-900">AI анализирует...</p>
                  <p className="text-sm text-gray-500">
                    Определяю технику, художника, период
                  </p>
                </div>
              </div>
            </div>
          ) : analyze.isError ? (
            <div className="flex flex-col items-center gap-4">
              {imagePreview && (
                <img
                  src={imagePreview}
                  alt=""
                  className="mx-auto h-48 rounded-lg object-contain"
                />
              )}
              <p className="text-sm text-red-600">
                Не удалось проанализировать. Проверьте API-ключ OpenRouter.
              </p>
              <button
                onClick={() => setStep("review")}
                className="rounded-lg border px-4 py-2 text-sm hover:bg-gray-50"
              >
                Заполнить вручную
              </button>
            </div>
          ) : (
            <>
              <Upload size={48} className="mx-auto mb-4 text-gray-400" />
              <p className="mb-2 text-lg font-medium text-gray-700">
                Перетащи фото или нажми для загрузки
              </p>
              <p className="mb-6 text-sm text-gray-400">
                AI автоматически определит технику, художника и заполнит карточку
              </p>
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-gray-900 px-6 py-3 text-sm font-medium text-white hover:bg-gray-800">
                <Sparkles size={16} />
                Загрузить фото
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFile(file);
                  }}
                />
              </label>
            </>
          )}
        </div>

        <button
          onClick={() => setStep("review")}
          className="mt-4 text-sm text-gray-400 underline hover:text-gray-600"
        >
          Или заполнить без фото
        </button>
      </div>
    );
  }

  // === Шаг 2: Ревью и правка AI-предложений ===
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-2 text-2xl font-bold text-gray-900">
        Новое произведение
      </h1>
      {aiSuggestion?.confidence && (
        <p className="mb-6 text-sm text-gray-500">
          <Sparkles size={14} className="mr-1 inline text-amber-500" />
          AI заполнил карточку (уверенность: {aiSuggestion.confidence}).
          Проверь и поправь если нужно.
        </p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
        className="space-y-5"
      >
        {/* Фото-превью */}
        <div className="flex gap-4 rounded-xl bg-white p-5 shadow-sm">
          {imagePreview ? (
            <div className="relative">
              <img
                src={imagePreview}
                alt=""
                className="h-40 w-40 rounded-lg object-cover"
              />
              <button
                type="button"
                onClick={() => {
                  setImageFile(null);
                  setImagePreview(null);
                }}
                className="absolute -right-2 -top-2 rounded-full bg-red-500 p-1 text-white"
              >
                <X size={12} />
              </button>
            </div>
          ) : (
            <label className="flex h-40 w-40 cursor-pointer items-center justify-center rounded-lg border-2 border-dashed text-gray-400 hover:border-gray-400">
              <Upload size={24} />
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    setImageFile(file);
                    setImagePreview(URL.createObjectURL(file));
                  }
                }}
              />
            </label>
          )}

          <div className="flex-1 space-y-3">
            {/* Название */}
            <div>
              <label className="mb-1 block text-xs text-gray-500">Название</label>
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                placeholder="AI подставит автоматически"
              />
            </div>

            {/* Художник */}
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Художник{" "}
                {aiSuggestion?.artist_name_suggestion &&
                  !aiSuggestion.artist && (
                    <span className="text-amber-600">
                      (AI: {aiSuggestion.artist_name_suggestion} — не найден в
                      базе)
                    </span>
                  )}
              </label>
              {form.new_artist_name && !form.artist_id ? (
                <div className="flex gap-2">
                  <input
                    value={form.new_artist_name}
                    onChange={(e) =>
                      setForm({ ...form, new_artist_name: e.target.value })
                    }
                    className="flex-1 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm"
                    placeholder="Имя нового художника"
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setForm({ ...form, new_artist_name: "", artist_id: 0 })
                    }
                    className="rounded-lg border px-3 py-2 text-xs text-gray-500"
                  >
                    Из базы
                  </button>
                </div>
              ) : (
                <select
                  value={form.artist_id}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      artist_id: Number(e.target.value),
                      new_artist_name: "",
                    })
                  }
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                  required={!form.new_artist_name}
                >
                  <option value={0}>Выберите художника</option>
                  {artists.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name_ru}
                      {a.name_en ? ` (${a.name_en})` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        </div>

        {/* Основные поля */}
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <div className="mb-4 grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-xs text-gray-500">Год</label>
              <input
                type="number"
                value={form.year}
                onChange={(e) => setForm({ ...form, year: e.target.value })}
                className="w-full rounded-lg border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Тираж</label>
              <input
                value={form.edition}
                onChange={(e) => setForm({ ...form, edition: e.target.value })}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                placeholder="12/50"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Состояние
              </label>
              <input
                value={form.condition}
                onChange={(e) =>
                  setForm({ ...form, condition: e.target.value })
                }
                className="w-full rounded-lg border px-3 py-2 text-sm"
                placeholder="AI заполнит"
              />
            </div>
          </div>

          {/* Техника */}
          <div className="mb-4">
            <label className="mb-2 block text-xs text-gray-500">Техника</label>
            <div className="max-h-40 space-y-2 overflow-y-auto rounded-lg border p-3">
              {Object.entries(grouped).map(([cat, techs]) => (
                <div key={cat}>
                  <p className="mb-1 text-[10px] font-semibold uppercase text-gray-400">
                    {cat}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {techs.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => toggleTechnique(t.id)}
                        className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs transition-colors ${
                          form.technique_ids.includes(t.id)
                            ? "bg-gray-900 text-white"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        }`}
                      >
                        {form.technique_ids.includes(t.id) && (
                          <Check size={10} />
                        )}
                        {t.name}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Описание */}
          <div>
            <label className="mb-1 block text-xs text-gray-500">
              Описание
              {aiSuggestion?.style_period && (
                <span className="ml-2 text-amber-600">
                  Стиль: {aiSuggestion.style_period}
                </span>
              )}
            </label>
            <textarea
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              rows={3}
              className="w-full rounded-lg border px-3 py-2 text-sm"
            />
          </div>
        </div>

        {/* Цены и локация */}
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Цена закупки (₽)
              </label>
              <input
                type="number"
                step="0.01"
                value={form.purchase_price}
                onChange={(e) =>
                  setForm({ ...form, purchase_price: e.target.value })
                }
                className="w-full rounded-lg border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Цена продажи (₽)
                {aiSuggestion?.estimated_price_rub && (
                  <span className="ml-1 text-amber-600">AI</span>
                )}
              </label>
              <input
                type="number"
                step="0.01"
                value={form.sale_price}
                onChange={(e) =>
                  setForm({ ...form, sale_price: e.target.value })
                }
                className="w-full rounded-lg border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Местоположение
              </label>
              <input
                value={form.location}
                onChange={(e) =>
                  setForm({ ...form, location: e.target.value })
                }
                className="w-full rounded-lg border px-3 py-2 text-sm"
                placeholder="Склад, адрес"
              />
            </div>
          </div>
        </div>

        {/* Кнопки */}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={create.isPending}
            className="flex items-center gap-2 rounded-lg bg-gray-900 px-6 py-2.5 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {create.isPending ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Check size={16} />
            )}
            Создать
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-lg border px-6 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            Отмена
          </button>
        </div>
      </form>
    </div>
  );
}
