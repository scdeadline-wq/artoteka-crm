"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, Edit3, Save, X, Trash2, ShoppingCart, Loader2, FileDown, Plus, Star, Undo2,
} from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import { useAuthStore, isAdmin as isAdminRole } from "@/lib/store";
import type { Artwork, Artist, Technique, Client, Room, Sale, StorageOption } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";
import { formatPrice, SUPPORTED_CURRENCIES } from "@/lib/currency";
// import ArtworkMockup from "@/components/mockup";  // скрыто, image-модель недоступна

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-200 text-gray-800",
  review: "bg-yellow-100 text-yellow-800",
  for_sale: "bg-green-100 text-green-800",
  reserved: "bg-blue-100 text-blue-800",
  sold: "bg-purple-100 text-purple-800",
  collection: "bg-orange-100 text-orange-800",
  on_exhibition: "bg-teal-100 text-teal-800",
};

const STATUS_FLOW: Record<string, string[]> = {
  draft: ["review", "for_sale"],
  review: ["for_sale", "draft"],
  for_sale: ["reserved", "collection", "on_exhibition"],
  reserved: ["for_sale", "sold"],
  sold: [],
  collection: ["for_sale", "on_exhibition"],
  on_exhibition: ["for_sale", "collection"],
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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showReserveModal, setShowReserveModal] = useState(false);
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfOpts, setPdfOpts] = useState({ provenance: true, purchase: false });
  const [newTech, setNewTech] = useState("");
  const [manualArtist, setManualArtist] = useState(false);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const user = useAuthStore((s) => s.user);
  const isAdmin = isAdminRole(user);

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

  const { data: rooms = [] } = useQuery<Room[]>({
    queryKey: ["rooms"],
    queryFn: () => api.get("/rooms/").then((r) => r.data),
    enabled: editing,
  });
  const { data: storage = [] } = useQuery<StorageOption[]>({
    queryKey: ["storage"],
    queryFn: () => api.get("/storage/").then((r) => r.data),
    enabled: editing,
  });
  const storageBy = (kind: string) => storage.filter((s) => s.kind === kind);

  const { data: clients = [] } = useQuery<Client[]>({
    queryKey: ["clients"],
    queryFn: () => api.get("/clients").then((r) => r.data),
    // Клиенты нужны: в модалке продажи, в модалке резерва и чтобы показать имя клиента в резерве
    enabled:
      showSellModal ||
      showReserveModal ||
      (artwork?.status === "reserved" && artwork?.reserved_client_id != null),
  });

  // Продажа этой работы (для отмены): GET /sales/ не фильтрует по artwork_id —
  // берём весь список (отсортирован по дате ↓) и ищем продажу на клиенте.
  const { data: sales = [] } = useQuery<Sale[]>({
    queryKey: ["sales"],
    queryFn: () => api.get("/sales").then((r) => r.data),
    enabled: artwork?.status === "sold",
  });
  const artworkSale = sales.find((s) => s.artwork_id === Number(id));

  // Edit form state
  const [form, setForm] = useState<Record<string, unknown>>({});

  function startEdit() {
    if (!artwork) return;
    setForm({
      title: artwork.title || "",
      artist_id: artwork.artist.id,
      new_artist_name: "",
      year: artwork.year || "",
      edition: artwork.edition || "",
      description: artwork.description || "",
      condition: artwork.condition || "",
      provenance: artwork.provenance || "",
      style_period: artwork.style_period || "",
      warehouse_id: artwork.warehouse?.id ?? 0,
      rack_id: artwork.rack?.id ?? 0,
      shelf_id: artwork.shelf?.id ?? 0,
      width_cm: artwork.width_cm || "",
      height_cm: artwork.height_cm || "",
      purchase_price: artwork.purchase_price || "",
      sale_price: artwork.sale_price || "",
      currency: artwork.currency || "USD",
      room_id: artwork.room?.id ?? 0,
      is_framed: !!artwork.is_framed,
      tags: (artwork.tags || []).join(", "),  // сырая строка — иначе запятая «съедается» при вводе
      technique_ids: artwork.techniques.map((t) => t.id),
    });
    setManualArtist(false);
    setNewTech("");
    setEditing(true);
  }

  // Добавить свою технику в справочник и сразу отметить её
  const addTechnique = useMutation({
    mutationFn: async (name: string) => {
      const { data } = await api.post("/techniques", { name });
      return data as Technique;
    },
    onSuccess: (tech) => {
      queryClient.invalidateQueries({ queryKey: ["techniques"] });
      setForm((f) => {
        const ids = (f.technique_ids as number[]) || [];
        return { ...f, technique_ids: ids.includes(tech.id) ? ids : [...ids, tech.id] };
      });
      setNewTech("");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      // Новый художник, которого нет в базе — создаём и берём его id
      let artistId = Number(form.artist_id) || 0;
      const newArtistName = ((form.new_artist_name as string) || "").trim();
      if (manualArtist && newArtistName) {
        const { data: newArtist } = await api.post("/artists", { name_ru: newArtistName });
        artistId = newArtist.id;
      }

      const tagsRaw = (form.tags as string) || "";
      const payload: Record<string, unknown> = {
        artist_id: artistId,
        year: form.year ? Number(form.year) : null,
        width_cm: form.width_cm ? Number(form.width_cm) : null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        sale_price: form.sale_price ? Number(form.sale_price) : null,
        currency: (form.currency as string) || undefined,
        title: form.title || null,
        edition: form.edition || null,
        description: form.description || null,
        condition: form.condition || null,
        provenance: form.provenance || null,
        style_period: form.style_period || null,
        warehouse_id: form.warehouse_id ? Number(form.warehouse_id) : null,
        rack_id: form.rack_id ? Number(form.rack_id) : null,
        shelf_id: form.shelf_id ? Number(form.shelf_id) : null,
        room_id: form.room_id ? Number(form.room_id) : null,
        is_framed: !!form.is_framed,
        tags: tagsRaw.split(",").map((t) => t.trim().replace(/^#/, "")).filter(Boolean),
        technique_ids: (form.technique_ids as number[]) || [],
      };
      // Закупочную цену передаём только если юзер — admin
      if (isAdmin) {
        payload.purchase_price = form.purchase_price ? Number(form.purchase_price) : null;
      }
      return api.put(`/artworks/${id}`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artists"] });
      setEditing(false);
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось сохранить изменения");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/artworks/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
      router.push("/artworks");
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setShowDeleteConfirm(false);
      setErrMsg(e?.response?.data?.detail || "Не удалось удалить работу");
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) =>
      api.patch(`/artworks/${id}/status`, null, { params: { status } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось сменить статус");
    },
  });

  // Резерв: статус + поля клиента/срока/заметки одним PUT (бэк применяет exclude_unset)
  const [reserveForm, setReserveForm] = useState({ client_id: 0, until: "", note: "" });
  const reserveMutation = useMutation({
    mutationFn: () =>
      api.put(`/artworks/${id}`, {
        status: "reserved",
        reserved_client_id: reserveForm.client_id || null,
        reserved_until: reserveForm.until || null,
        reserve_note: reserveForm.note.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
      setShowReserveModal(false);
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось оформить резерв");
    },
  });

  // Отмена продажи: продажа удаляется, работа возвращается в статус «В продаже»
  const cancelSaleMutation = useMutation({
    mutationFn: (saleId: number) => api.delete(`/sales/${saleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось отменить продажу");
    },
  });

  // === Управление фото (доступно всегда, не только в режиме редактирования) ===
  const uploadImageMutation = useMutation({
    // ВАЖНО: URL обязан кончаться на «/» — иначе FastAPI отвечает 307 и фото грузится дважды
    mutationFn: ({ file, internal }: { file: File; internal?: boolean }) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post(`/artworks/${id}/images/`, fd, internal ? { params: { is_internal: true } } : undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось загрузить фото");
    },
  });

  const deleteImageMutation = useMutation({
    mutationFn: (imageId: number) => api.delete(`/artworks/${id}/images/${imageId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось удалить фото");
    },
  });

  const setInternalMutation = useMutation({
    mutationFn: ({ imageId, internal }: { imageId: number; internal: boolean }) =>
      api.patch(`/artworks/${id}/images/${imageId}/`, null, { params: { is_internal: internal } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
    },
  });

  const setPrimaryImageMutation = useMutation({
    // Слэш в конце пути — до query-строки (params), иначе 307
    mutationFn: (imageId: number) =>
      api.patch(`/artworks/${id}/images/${imageId}/`, null, { params: { is_primary: true } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось сделать фото главным");
    },
  });

  // Sell modal state
  const [sellForm, setSellForm] = useState({
    client_id: 0,
    referral_id: 0,
    sold_price: "",
    referral_fee: "",
    currency: "",
  });

  const sellMutation = useMutation({
    mutationFn: () =>
      api.post("/sales", {
        artwork_id: Number(id),
        client_id: sellForm.client_id,
        referral_id: sellForm.referral_id || null,
        sold_price: Number(sellForm.sold_price),
        referral_fee: sellForm.referral_fee ? Number(sellForm.referral_fee) : null,
        currency: sellForm.currency || artwork?.currency || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artwork", id] });
      queryClient.invalidateQueries({ queryKey: ["artworks"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setShowSellModal(false);
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setShowSellModal(false);
      setErrMsg(e?.response?.data?.detail || "Не удалось оформить продажу");
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
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <Link
          href="/artworks"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft size={16} /> Назад
        </Link>
        <div className="flex flex-wrap gap-2">
          {!editing && (
            <button
              onClick={() => setShowPdfModal(true)}
              className="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              <FileDown size={14} /> PDF
            </button>
          )}
          {!editing && artwork.status === "sold" && (
            <button
              onClick={() => {
                if (!artworkSale) {
                  setErrMsg("Продажа не найдена — обновите страницу");
                  return;
                }
                if (window.confirm('Продажа будет удалена, работа вернётся в статус "В продаже". Продолжить?')) {
                  cancelSaleMutation.mutate(artworkSale.id);
                }
              }}
              disabled={cancelSaleMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              {cancelSaleMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Undo2 size={14} />}
              Отменить продажу
            </button>
          )}
          {!editing && artwork.status !== "sold" && (
            <button
              onClick={() => {
                setSellForm({
                  client_id: 0,
                  referral_id: 0,
                  sold_price: artwork.sale_price ? String(artwork.sale_price) : "",
                  referral_fee: "",
                  currency: artwork.currency || "",
                });
                setShowSellModal(true);
              }}
              className="flex items-center gap-1.5 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500"
            >
              <ShoppingCart size={14} /> Продать
            </button>
          )}
          {!editing && isAdmin && (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-1.5 rounded-lg border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              <Trash2 size={14} /> Удалить
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

      {errMsg && (
        <div className="mb-4 flex items-center justify-between rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          <span>{errMsg}</span>
          <button onClick={() => setErrMsg(null)} aria-label="Закрыть">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Основная карточка */}
      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        {/* Заголовок и статус */}
        <div className="mb-4 flex items-start justify-between">
          <div>
            {editing ? (
              <>
                {manualArtist ? (
                  <div className="flex items-center gap-2">
                    <input
                      value={(form.new_artist_name as string) || ""}
                      onChange={(e) => setForm({ ...form, new_artist_name: e.target.value })}
                      className="rounded border border-amber-300 bg-amber-50 px-2 py-1 text-lg font-semibold"
                      placeholder="Имя нового художника"
                      autoFocus
                    />
                    <button
                      type="button"
                      onClick={() => { setManualArtist(false); setForm({ ...form, new_artist_name: "" }); }}
                      className="rounded border px-2 py-1 text-xs text-gray-500"
                    >
                      Из базы
                    </button>
                  </div>
                ) : (
                  <select
                    value={form.artist_id as number}
                    onChange={(e) => {
                      if (e.target.value === "new") { setManualArtist(true); return; }
                      setForm({ ...form, artist_id: Number(e.target.value) });
                    }}
                    className="rounded border px-2 py-1 text-lg font-semibold"
                  >
                    {artists.map((a) => (
                      <option key={a.id} value={a.id}>{a.name_ru}</option>
                    ))}
                    <option value="new">+ Добавить нового художника…</option>
                  </select>
                )}
                <input
                  value={form.title as string}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="mt-1 block text-lg text-gray-700 border-b border-blue-300 focus:outline-none"
                  placeholder="Название"
                />
              </>
            ) : (
              <>
                {/* Художник — жирным сверху (ссылка на его работы), название — обычным под ним */}
                <h1 className="text-2xl font-bold text-gray-900">
                  <Link
                    href={`/artworks?artist=${artwork.artist.id}`}
                    className="hover:text-blue-600 hover:underline"
                  >
                    {artwork.artist.name_ru}
                  </Link>
                </h1>
                <p className="mt-1 text-lg text-gray-700">
                  {artwork.title || "Без названия"}
                  {artwork.year ? `, ${artwork.year}` : ""}
                </p>
              </>
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
                    onClick={() => {
                      // Перевод в резерв — через модалку (клиент / срок / заметка)
                      if (s === "reserved") {
                        setReserveForm({
                          client_id: artwork.reserved_client_id ?? 0,
                          until: artwork.reserved_until ?? "",
                          note: artwork.reserve_note ?? "",
                        });
                        setShowReserveModal(true);
                        return;
                      }
                      statusMutation.mutate(s);
                    }}
                    className="rounded border px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-100"
                  >
                    → {STATUS_LABELS[s]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Инфо о резерве: для кого, до когда, заметка */}
        {artwork.status === "reserved" &&
          (artwork.reserved_client_id || artwork.reserved_until || artwork.reserve_note) && (
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
            <p className="font-medium">
              Резерв
              {artwork.reserved_client_id && (
                <>
                  {" — для "}
                  {clients.find((c) => c.id === artwork.reserved_client_id)?.name ||
                    `клиента #${artwork.reserved_client_id}`}
                </>
              )}
              {artwork.reserved_until &&
                ` · держим до ${new Date(artwork.reserved_until).toLocaleDateString("ru")}`}
            </p>
            {artwork.reserve_note && (
              <p className="mt-1 text-blue-800">{artwork.reserve_note}</p>
            )}
          </div>
        )}

        {/* Фото: добавить / удалить / сделать главным — доступно всегда */}
        <div className="mb-6">
          {hasImages && (
            <div className="flex gap-3 overflow-x-auto pb-1">
              {artwork.images.map((img) => (
                <div key={img.id} className="group relative shrink-0">
                  <img
                    src={imageUrl(img.url)}
                    alt=""
                    className="h-56 rounded-lg object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm("Удалить это фото?")) {
                        deleteImageMutation.mutate(img.id);
                      }
                    }}
                    disabled={deleteImageMutation.isPending}
                    title="Удалить фото"
                    className="absolute right-1.5 top-1.5 rounded-full bg-black/50 p-1 text-white hover:bg-red-600 disabled:opacity-50"
                  >
                    <X size={14} />
                  </button>
                  {img.is_internal ? (
                    <span className="absolute bottom-1.5 left-1.5 flex items-center gap-1 rounded-full bg-gray-700/80 px-2 py-0.5 text-xs text-white" title="Внутреннее фото — не попадает в клиентский PDF">
                      🔒 Внутр.
                    </span>
                  ) : img.is_primary ? (
                    <span className="absolute bottom-1.5 left-1.5 flex items-center gap-1 rounded-full bg-black/50 px-2 py-0.5 text-xs text-white">
                      <Star size={10} className="fill-amber-400 text-amber-400" /> Главное
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setPrimaryImageMutation.mutate(img.id)}
                      disabled={setPrimaryImageMutation.isPending}
                      className="absolute bottom-1.5 left-1.5 flex items-center gap-1 rounded-full bg-black/50 px-2 py-0.5 text-xs text-white hover:bg-black/70 disabled:opacity-50"
                    >
                      <Star size={10} /> Сделать главным
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setInternalMutation.mutate({ imageId: img.id, internal: !img.is_internal })}
                    disabled={setInternalMutation.isPending}
                    title={img.is_internal ? "Показывать в каталоге и клиентском PDF" : "Скрыть из клиентского PDF (внутреннее)"}
                    className="absolute bottom-1.5 right-1.5 rounded-full bg-black/50 px-2 py-0.5 text-xs text-white hover:bg-black/70 disabled:opacity-50"
                  >
                    {img.is_internal ? "→ в PDF" : "скрыть из PDF"}
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
              {uploadImageMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              {uploadImageMutation.isPending ? "Загружаю..." : "Добавить фото"}
              <input
                type="file"
                accept="image/*"
                className="hidden"
                disabled={uploadImageMutation.isPending}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadImageMutation.mutate({ file });
                  e.target.value = "";
                }}
              />
            </label>
            <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-dashed px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-50" title="Сертификат, оборот картины и т.п. — не уходит в клиентский PDF">
              <Plus size={14} /> Внутр. документ
              <input
                type="file"
                accept="image/*"
                className="hidden"
                disabled={uploadImageMutation.isPending}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadImageMutation.mutate({ file, internal: true });
                  e.target.value = "";
                }}
              />
            </label>
          </div>
        </div>

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
              <label className="mb-1 block text-xs text-gray-500">Склад / адрес</label>
              <select value={(form.warehouse_id as number) || 0} onChange={(e) => setForm({ ...form, warehouse_id: Number(e.target.value) })} className="w-full rounded border px-2 py-1.5 text-sm">
                <option value={0}>— не указан —</option>
                {storageBy("warehouse").map((s) => (<option key={s.id} value={s.id}>{s.name}</option>))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Стеллаж</label>
              <select value={(form.rack_id as number) || 0} onChange={(e) => setForm({ ...form, rack_id: Number(e.target.value) })} className="w-full rounded border px-2 py-1.5 text-sm">
                <option value={0}>— не указан —</option>
                {storageBy("rack").map((s) => (<option key={s.id} value={s.id}>{s.name}</option>))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Полка</label>
              <select value={(form.shelf_id as number) || 0} onChange={(e) => setForm({ ...form, shelf_id: Number(e.target.value) })} className="w-full rounded border px-2 py-1.5 text-sm">
                <option value={0}>— не указана —</option>
                {storageBy("shelf").map((s) => (<option key={s.id} value={s.id}>{s.name}</option>))}
              </select>
            </div>
            {isAdmin && (
              <div>
                <label className="mb-1 block text-xs text-gray-500">Цена закупки</label>
                <input type="number" value={form.purchase_price as string} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
              </div>
            )}
            <div>
              <label className="mb-1 block text-xs text-gray-500">Цена продажи</label>
              <input type="number" value={form.sale_price as string} onChange={(e) => setForm({ ...form, sale_price: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Валюта</label>
              <select value={(form.currency as string) || "USD"} onChange={(e) => setForm({ ...form, currency: e.target.value })} className="w-full rounded border px-2 py-1.5 text-sm">
                {SUPPORTED_CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Комната</label>
              <select
                value={(form.room_id as number) || 0}
                onChange={(e) => setForm({ ...form, room_id: Number(e.target.value) })}
                className="w-full rounded border px-2 py-1.5 text-sm"
              >
                <option value={0}>— не указана —</option>
                {rooms.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={!!form.is_framed} onChange={(e) => setForm({ ...form, is_framed: e.target.checked })} />
                В раме
              </label>
            </div>
            <div className="col-span-full">
              <label className="mb-1 block text-xs text-gray-500">Стиль / направление</label>
              <input value={form.style_period as string} onChange={(e) => setForm({ ...form, style_period: e.target.value })} placeholder="напр. Импрессионизм, 1960-е" className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div className="col-span-full">
              <label className="mb-1 block text-xs text-gray-500">Теги (через запятую, без #)</label>
              <input
                value={(form.tags as string) || ""}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                placeholder="пейзаж, абстракция, портрет"
                className="w-full rounded border px-2 py-1.5 text-sm"
              />
            </div>
            <div className="col-span-full">
              <label className="mb-1 block text-xs text-gray-500">Описание</label>
              <textarea value={form.description as string} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div className="col-span-full">
              <label className="mb-1 block text-xs text-gray-500">Провенанс (биография работы: коллекции, выставки, каталоги)</label>
              <textarea value={form.provenance as string} onChange={(e) => setForm({ ...form, provenance: e.target.value })} rows={3} className="w-full rounded border px-2 py-1.5 text-sm" placeholder="Из собрания…; участвовала в выставке…; упоминается в каталоге…" />
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
              {/* Своя техника */}
              <div className="mt-2 flex gap-2">
                <input
                  value={newTech}
                  onChange={(e) => setNewTech(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      if (newTech.trim()) addTechnique.mutate(newTech.trim());
                    }
                  }}
                  placeholder="Своя техника (напр. «Левкас, темпера»)"
                  className="flex-1 rounded border px-2 py-1.5 text-sm"
                />
                <button
                  type="button"
                  onClick={() => newTech.trim() && addTechnique.mutate(newTech.trim())}
                  disabled={!newTech.trim() || addTechnique.isPending}
                  className="flex items-center gap-1 rounded border px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  {addTechnique.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                  Добавить
                </button>
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
            {artwork.style_period && (
              <div className="col-span-2">
                <p className="text-gray-500">Стиль / направление</p>
                <p className="font-medium">{artwork.style_period}</p>
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
            {artwork.warehouse && (
              <div>
                <p className="text-gray-500">Склад / адрес</p>
                <p className="font-medium">{artwork.warehouse.name}</p>
              </div>
            )}
            {artwork.rack && (
              <div>
                <p className="text-gray-500">Стеллаж</p>
                <p className="font-medium">{artwork.rack.name}</p>
              </div>
            )}
            {artwork.shelf && (
              <div>
                <p className="text-gray-500">Полка</p>
                <p className="font-medium">{artwork.shelf.name}</p>
              </div>
            )}
            {artwork.condition && (
              <div>
                <p className="text-gray-500">Состояние</p>
                <p className="font-medium">{artwork.condition}</p>
              </div>
            )}
            {isAdmin && artwork.purchase_price != null && (
              <div>
                <p className="text-gray-500">Цена закупки</p>
                <p className="font-medium">{formatPrice(artwork.purchase_price, artwork.currency)}</p>
              </div>
            )}
            {artwork.sale_price != null && (
              <div>
                <p className="text-gray-500">Цена продажи</p>
                <p className="font-semibold text-green-700">{formatPrice(artwork.sale_price, artwork.currency)}</p>
              </div>
            )}
            {artwork.room && (
              <div>
                <p className="text-gray-500">Комната</p>
                <p className="font-medium">{artwork.room.name}</p>
              </div>
            )}
            <div>
              <p className="text-gray-500">В раме</p>
              <p className="font-medium">{artwork.is_framed ? "Да" : "Нет"}</p>
            </div>
            {artwork.tags && artwork.tags.length > 0 && (
              <div className="col-span-full">
                <p className="text-gray-500">Теги</p>
                <p className="font-medium">{artwork.tags.map((t) => `#${t}`).join(" ")}</p>
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
        {!editing && artwork.provenance && (
          <div className="mt-4 border-t pt-4">
            <p className="mb-1 text-sm text-gray-500">Провенанс</p>
            <p className="whitespace-pre-line text-sm leading-relaxed text-gray-700">{artwork.provenance}</p>
          </div>
        )}
      </div>

      {/* Мокапы скрыты до появления рабочей image-модели (gpt-5-image / gemini блокируют RU IP).
          Компонент ArtworkMockup и стр. /mockup в коде остались — раскомментировать здесь и в sidebar.tsx, когда вернём. */}

      {/* Модалка подтверждения удаления */}
      {showPdfModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-3 text-lg font-bold text-gray-900">PDF для клиента</h2>
            <p className="mb-3 text-xs text-gray-500">Что включить в выгружаемый файл. Лого и водяной знак настраиваются в «Настройках».</p>
            <label className="mb-2 flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={pdfOpts.provenance} onChange={(e) => setPdfOpts({ ...pdfOpts, provenance: e.target.checked })} />
              Включить провенанс (биографию работы)
            </label>
            {isAdmin && (
              <label className="mb-2 flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={pdfOpts.purchase} onChange={(e) => setPdfOpts({ ...pdfOpts, purchase: e.target.checked })} />
                Включить закупочную цену (обычно НЕ для клиента)
              </label>
            )}
            <div className="mt-4 flex gap-3">
              <button
                onClick={async () => {
                  try {
                    const res = await api.get(`/artworks/${id}/pdf/`, {
                      responseType: "blob",
                      params: { include_provenance: pdfOpts.provenance, include_purchase_price: pdfOpts.purchase },
                    });
                    const url = URL.createObjectURL(res.data as Blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `artoteka_${artwork.inventory_number}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    setTimeout(() => URL.revokeObjectURL(url), 60_000);
                    setShowPdfModal(false);
                  } catch {
                    alert("Не удалось сформировать PDF");
                  }
                }}
                className="flex-1 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
              >
                Скачать PDF
              </button>
              <button onClick={() => setShowPdfModal(false)} className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-bold text-gray-900">Удалить работу?</h2>
            <p className="mb-1 text-sm text-gray-700">
              «{artwork.title || "Без названия"}» — {artwork.artist.name_ru}
            </p>
            <p className="mb-4 text-xs text-gray-500">
              Работа уйдёт в корзину — её можно восстановить позже.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="flex-1 rounded-lg bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Удаляю..." : "Удалить"}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модалка резерва */}
      {showReserveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-bold text-gray-900">Поставить в резерв</h2>
            <p className="mb-4 text-sm text-gray-500">
              {artwork.title || "Без названия"} — {artwork.artist.name_ru}
            </p>

            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs text-gray-500">Клиент</label>
                <select
                  value={reserveForm.client_id}
                  onChange={(e) => setReserveForm({ ...reserveForm, client_id: Number(e.target.value) })}
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                >
                  <option value={0}>Не указан</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Держим до</label>
                <input
                  type="date"
                  value={reserveForm.until}
                  onChange={(e) => setReserveForm({ ...reserveForm, until: e.target.value })}
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Заметка</label>
                <textarea
                  value={reserveForm.note}
                  onChange={(e) => setReserveForm({ ...reserveForm, note: e.target.value })}
                  rows={2}
                  placeholder="напр. ждёт перевода, просил не звонить до пятницы"
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="mt-5 flex gap-3">
              <button
                onClick={() => reserveMutation.mutate()}
                disabled={reserveMutation.isPending}
                className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {reserveMutation.isPending ? "Сохраняю..." : "В резерв"}
              </button>
              <button
                onClick={() => setShowReserveModal(false)}
                className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Отмена
              </button>
            </div>
          </div>
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
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="mb-1 block text-xs text-gray-500">Цена продажи *</label>
                  <input
                    type="number"
                    value={sellForm.sold_price}
                    onChange={(e) => setSellForm({ ...sellForm, sold_price: e.target.value })}
                    className="w-full rounded-lg border px-3 py-2 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-gray-500">Валюта</label>
                  <select
                    value={sellForm.currency || artwork.currency || "USD"}
                    onChange={(e) => setSellForm({ ...sellForm, currency: e.target.value })}
                    className="w-full rounded-lg border px-3 py-2 text-sm"
                  >
                    {SUPPORTED_CURRENCIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-gray-500">Реферальный взнос</label>
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
