"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Artist, Technique } from "@/lib/types";

export default function NewArtworkPage() {
  const router = useRouter();

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
    year: "",
    edition: "",
    description: "",
    location: "",
    purchase_price: "",
    sale_price: "",
    status: "draft",
    technique_ids: [] as number[],
  });

  const create = useMutation({
    mutationFn: () =>
      api.post("/artworks", {
        ...form,
        artist_id: form.artist_id,
        year: form.year ? Number(form.year) : null,
        purchase_price: form.purchase_price ? Number(form.purchase_price) : null,
        sale_price: form.sale_price ? Number(form.sale_price) : null,
        edition: form.edition || null,
        description: form.description || null,
        location: form.location || null,
      }),
    onSuccess: () => router.push("/artworks"),
  });

  function toggleTechnique(id: number) {
    setForm((f) => ({
      ...f,
      technique_ids: f.technique_ids.includes(id)
        ? f.technique_ids.filter((t) => t !== id)
        : [...f.technique_ids, id],
    }));
  }

  // Group techniques by category
  const grouped = techniques.reduce<Record<string, Technique[]>>((acc, t) => {
    const cat = t.category || "Прочее";
    (acc[cat] = acc[cat] || []).push(t);
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        Новое произведение
      </h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
        className="space-y-5 rounded-xl bg-white p-6 shadow-sm"
      >
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Художник *
          </label>
          <select
            value={form.artist_id}
            onChange={(e) => setForm({ ...form, artist_id: Number(e.target.value) })}
            className="w-full rounded-lg border px-3 py-2 text-sm"
            required
          >
            <option value={0} disabled>
              Выберите художника
            </option>
            {artists.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name_ru} {a.name_en ? `(${a.name_en})` : ""}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Название
          </label>
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full rounded-lg border px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Год
            </label>
            <input
              type="number"
              value={form.year}
              onChange={(e) => setForm({ ...form, year: e.target.value })}
              className="w-full rounded-lg border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Тираж
            </label>
            <input
              value={form.edition}
              onChange={(e) => setForm({ ...form, edition: e.target.value })}
              className="w-full rounded-lg border px-3 py-2 text-sm"
              placeholder="напр. 12/50"
            />
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Техника
          </label>
          <div className="max-h-48 space-y-3 overflow-y-auto rounded-lg border p-3">
            {Object.entries(grouped).map(([cat, techs]) => (
              <div key={cat}>
                <p className="mb-1 text-xs font-semibold text-gray-400 uppercase">
                  {cat}
                </p>
                <div className="flex flex-wrap gap-2">
                  {techs.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => toggleTechnique(t.id)}
                      className={`rounded-full px-3 py-1 text-xs transition-colors ${
                        form.technique_ids.includes(t.id)
                          ? "bg-gray-900 text-white"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {t.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Описание
          </label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={3}
            className="w-full rounded-lg border px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Местоположение
          </label>
          <input
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Склад, адрес..."
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Цена закупки (₽)
            </label>
            <input
              type="number"
              step="0.01"
              value={form.purchase_price}
              onChange={(e) => setForm({ ...form, purchase_price: e.target.value })}
              className="w-full rounded-lg border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Цена продажи (₽)
            </label>
            <input
              type="number"
              step="0.01"
              value={form.sale_price}
              onChange={(e) => setForm({ ...form, sale_price: e.target.value })}
              className="w-full rounded-lg border px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            className="rounded-lg bg-gray-900 px-6 py-2 text-sm font-medium text-white hover:bg-gray-800"
          >
            Создать
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-lg border px-6 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Отмена
          </button>
        </div>
      </form>
    </div>
  );
}
