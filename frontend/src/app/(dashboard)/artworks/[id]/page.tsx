"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, Edit3, Save, X, Trash2, ShoppingCart, Loader2,
} from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import type { Artwork, Artist, Technique, Client } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";
import ArtworkMockup from "@/components/mockup";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-200 text-gray-800",
  review: "bg-yellow-100 text-yellow-800",
  for_sale: "bg-green-100 text-green-800",
  reserved: "bg-blue-100 text-blue-800",
  sold: "bg-purple-100 text-purple-800",
  collection: "bg-orange-100 text-orange-800",
};

const STATUS_FLOW: Record<string, string[]> = {
  draft: ["review", "for_sale"],
  review: ["for_sale", "draft"],
  for_sale: ["reserved", "collection"],
  reserved: ["for_sale", "sold"],
  sold: [],
  collection: ["for_sale"],
};

export default function ArtworkDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [showSellModal, setShowSellModal] = useState(false);

  const { data: artwork, isLoading } = useQuery<Artwork>({
    queryKey: ["artwork", id],
    queryFn: () => api.get(`/artworks/${id}`).then((r) => r.data),
  });

  const { data: artists = [] } = useQuery<Artist[]>({
    queryKey: ["artists"],
    queryFn: () => api.get("/artists").then((r) => r.data),
    enabled: editing,
  });

  const { data: techniques = [] } = useQuery<Technique[]>({
    queryKey: ["techniques"],
    queryFn: () => api.get("/techniques").then((r) => r.data),
    enabled: editing,
  });

  const { data: clients = [] } = useQuery<Client[]>({
    queryKey: ["clients"],
    queryFn: () => api.get("/clients").then((r) => r.data),
    enabled: showSellModal,
  });

  // Edit form state
  const [form, setForm] = useState<Record<string, unknown>>({});

  function startEdit() {
    if (!artwork) return;
    setForm({
      title: artwork.title || "",
      artist_id: artwork.artist.id,
      year: artwork.year || "",
      edition: artwork.edition || "",
      description: artwork.description || "",
      condition: artwork.condition || "",
      location: artwork.location || "",
      width_cm: artwork.width_cm || "",
      height_cm: artwork.height_cm || "",
      purchase_price: artwork.purchase_price || "",
      sale_price: artwork.sale_price || "",
      technique_ids: artwork.techniques.map((t) => t.id),
    });
    setEditing(true);
  }

  const updateMutation = useMutation({
    mutationFn: () =>
      api.put(`/artworks/${id}`, {
        ...form,
        year: form.year ? Number(form.year) : null,
        width_cm: form.width_cm ? Number(form.width_cm) : null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        purchase_price: form.purchase_price ? Number(form.purchase_price) : null,
        sale_price: form.sale_price ? Number(form.sale_price) : null,
        title: form.title || null,
        edition: form.edition || null,
        description: form.description || null,
        condition: form.condition || null,
        location: form.location || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      setEditing(false);
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) =>
      api.patch(`/artworks/${id}/status`, null, { params: { status } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["artwork", id] }),
  });

  // Sell modal state
  const [sellForm, setSellForm] = useState({
    client_id: 0,
    referral_id: 0,
    sold_price: "",
    referral_fee: "",
  });

  const sellMutation = useMutation({
    mutationFn: () =>
      api.post("/sales", {
        artwork_id: Number(id),
        client_id: sellForm.client_id,
        referral_id: sellForm.referral_id || null,
        sold_price: Number(sellForm.sold_price),
        referral_fee: sellForm.referral_fee ? Number(sellForm.referral_fee) : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      setShowSellModal(false);
    },
  });

  if (isLoading) return <p className="text-gray-500">Загрузка...</p>;
  if (!artwork) return <p className="text-red-500">Не найдено</p>;

  const hasImages = artwork.images.length > 0;
  const nextStatuses = STATUS_FLOW[artwork.status] || [];
  const widthCm = artwork.width_cm as number | null;
  const heightCm = artwork.height_cm as number | null;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex items-center justify-between">
        <Link
          href="/artworks"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft size={16} /> Назад
        </Link>
        <div className="flex gap-2">
          {!editing && artwork.status !== "sold" && (
            <button
              onClick={() => {
                setSellForm({
                  client_id: 0,
                  referral_id: 0,
                  sold_price: artwork.sale_price ? String(artwork.sale_price) : "",
                  referral_fee: "",
                });
                setShowSellModal(true);
              }}
              className="flex items-center gap-1.5 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500"
            >
              <ShoppingCart size={14} /> Продать
            </button>
          )}
          {!editing ? (
            <button
              onClick={startEdit}
              className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
            >
              <Edit3 size={14} /> Редактировать
            </button>
          ) : (
            <>
              <button
                onClick={() => updateMutation.mutate()}
                disabled={updateMutation.isPending}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {updateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Сохранить
              </button>
              <button
                onClick={() => setEditing(false)}
                className="flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                <X size={14} /> Отмена
              </button>
            </>
          )}
        </div>
      </div>

      {/* Основная карточка */}
      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        {/* Заголовок и статус */}
        <div className="mb-4 flex items-start justify-between">
          <div>
            {editing ? (
              <input
                value={form.title as string}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="text-2xl font-bold text-gray-900 border-b border-blue-300 focus:outline-none"
                placeholder="Название"
              />
            ) : (
              <h1 className="text-2xl font-bold text-gray-900">
                {artwork.title || "Без названия"}
              </h1>
            )}
            {editing ? (
              <select
                value={form.artist_id as number}
                onChange={(e) => setForm({ ...form, artist_id: Number(e.target.value) })}
                className="mt-1 rounded border px-2 py-1 text-sm"
              >
                {artists.map((a) => (
                  <option key={a.id} value={a.id}>{a.name_ru}</option>
                ))}
              </select>
            ) : (
              <p className="mt-1 text-gray-600">
                <Link href={`/artists`} className="hover:text-blue-600 hover:underline">
                  {artwork.artist.name_ru}
                </Link>
                {artwork.year ? `, ${artwork.year}` : ""}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className={`rounded-full px-3 py-1 text-sm font-medium ${STATUS_COLORS[artwork.status] || ""}`}>
              {STATUS_LABELS[artwork.status] || artwork.status}
            </span>
            {!editing && nextStatuses.length > 0 && (
              <div className="flex gap-1">
                {nextStatuses.map((s) => (
                  <button
                    key={s}
                    onClick={() => statusMutation.mutate(s)}
                    className="rounded border px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-100"
                  >
                    → {STATUS_LABELS[s]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Фото */}
        {hasImages && (
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

        {/* Поля */}
        {editing ? (
          <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-gray-500">Год</label>
              <input type="number" value={form.year as string} onChange={(e) => setForm({ ...form, year: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Тираж</label>
              <input value={form.edition as string} onChange={(e) => setForm({ ...form, edition: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Состояние</label>
              <input value={form.condition as string} onChange={(e) => setForm({ ...form, condition: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Ширина (см)</label>
              <input type="number" value={form.width_cm as string} onChange={(e) => setForm({ ...form, width_cm: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Высота (см)</label>
              <input type="number" value={form.height_cm as string} onChange={(e) => setForm({ ...form, height_cm: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Местоположение</label>
              <input value={form.location as string} onChange={(e) => setForm({ ...form, location: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Цена закупки (₽)</label>
              <input type="number" value={form.purchase_price as string} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Цена продажи (₽)</label>
              <input type="number" value={form.sale_price as string} onChange={(e) => setForm({ ...form, sale_price: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div className="col-span-full">
              <label className="mb-1 block text-xs text-gray-500">Описание</label>
              <textarea value={form.description as string} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div className="col-span-full">
              <label className="mb-2 block text-xs text-gray-500">Техника</label>
              <div className="flex flex-wrap gap-1.5">
                {techniques.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => {
                      const ids = form.technique_ids as number[];
                      setForm({
                        ...form,
                        technique_ids: ids.includes(t.id) ? ids.filter((x) => x !== t.id) : [...ids, t.id],
                      });
                    }}
                    className={`rounded-full px-2.5 py-1 text-xs ${
                      (form.technique_ids as number[]).includes(t.id)
                        ? "bg-gray-900 text-white"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
            <div>
              <p className="text-gray-500">Инвентарный номер</p>
              <p className="font-medium">#{artwork.inventory_number}</p>
            </div>
            {artwork.techniques.length > 0 && (
              <div className="col-span-2">
                <p className="text-gray-500">Техника</p>
                <p className="font-medium">{artwork.techniques.map((t) => t.name).join(", ")}</p>
              </div>
            )}
            {(widthCm || heightCm) && (
              <div>
                <p className="text-gray-500">Размер</p>
                <p className="font-medium">
                  {widthCm && heightCm ? `${widthCm} × ${heightCm} см` : widthCm ? `${widthCm} см (ш)` : `${heightCm} см (в)`}
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
            {artwork.condition && (
              <div>
                <p className="text-gray-500">Состояние</p>
                <p className="font-medium">{artwork.condition}</p>
              </div>
            )}
            {artwork.purchase_price != null && (
              <div>
                <p className="text-gray-500">Цена закупки</p>
                <p className="font-medium">{Number(artwork.purchase_price).toLocaleString("ru")} ₽</p>
              </div>
            )}
            {artwork.sale_price != null && (
              <div>
                <p className="text-gray-500">Цена продажи</p>
                <p className="font-semibold text-green-700">{Number(artwork.sale_price).toLocaleString("ru")} ₽</p>
              </div>
            )}
          </div>
        )}

        {!editing && artwork.description && (
          <div className="mt-4 border-t pt-4">
            <p className="mb-1 text-sm text-gray-500">Описание</p>
            <p className="text-sm leading-relaxed text-gray-700">{artwork.description}</p>
          </div>
        )}
      </div>

      {/* Мокапы скрыты — image-модель сейчас недоступна (geo-блок RU) */}
      {false && hasImages && (
        <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">В интерьере</h2>
          <ArtworkMockup artworkId={artwork.id} />
        </div>
      )}

      {/* Модалка продажи */}
      {showSellModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-bold text-gray-900">Оформить продажу</h2>
            <p className="mb-4 text-sm text-gray-500">
              {artwork.title} — {artwork.artist.name_ru}
            </p>

            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs text-gray-500">Покупатель *</label>
                <select
                  value={sellForm.client_id}
                  onChange={(e) => setSellForm({ ...sellForm, client_id: Number(e.target.value) })}
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                  required
                >
                  <option value={0}>Выберите</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Реферал</label>
                <select
                  value={sellForm.referral_id}
                  onChange={(e) => setSellForm({ ...sellForm, referral_id: Number(e.target.value) })}
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                >
                  <option value={0}>Без реферала</option>
                  {clients.filter((c) => c.client_type === "referral" || c.client_type === "dealer").map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs text-gray-500">Цена продажи (₽) *</label>
                  <input
                    type="number"
                    value={sellForm.sold_price}
                    onChange={(e) => setSellForm({ ...sellForm, sold_price: e.target.value })}
                    className="w-full rounded-lg border px-3 py-2 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-gray-500">Реферальный % (₽)</label>
                  <input
                    type="number"
                    value={sellForm.referral_fee}
                    onChange={(e) => setSellForm({ ...sellForm, referral_fee: e.target.value })}
                    className="w-full rounded-lg border px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </div>

            <div className="mt-5 flex gap-3">
              <button
                onClick={() => sellMutation.mutate()}
                disabled={!sellForm.client_id || !sellForm.sold_price || sellMutation.isPending}
                className="flex-1 rounded-lg bg-green-600 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:opacity-50"
              >
                {sellMutation.isPending ? "Оформляю..." : "Оформить продажу"}
              </button>
              <button
                onClick={() => setShowSellModal(false)}
                className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
