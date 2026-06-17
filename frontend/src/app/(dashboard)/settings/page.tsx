"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { imageUrl } from "@/lib/image";
import { useAuthStore, isAdmin as isAdminRole } from "@/lib/store";
import type { AppSettings } from "@/lib/types";
import { SUPPORTED_CURRENCIES } from "@/lib/currency";

export default function SettingsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const isAdmin = isAdminRole(user);

  useEffect(() => {
    if (user && !isAdmin) router.replace("/artworks");
  }, [user, isAdmin, router]);

  const { data } = useQuery<AppSettings>({
    queryKey: ["settings"],
    queryFn: () => api.get("/settings/").then((r) => r.data),
  });

  const [form, setForm] = useState({
    default_currency: "USD",
    gallery_name: "",
    pdf_logo_url: "",
    pdf_watermark_enabled: false,
    pdf_watermark_text: "",
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) {
      setForm({
        default_currency: data.default_currency,
        gallery_name: data.gallery_name || "",
        pdf_logo_url: data.pdf_logo_url || "",
        pdf_watermark_enabled: data.pdf_watermark_enabled,
        pdf_watermark_text: data.pdf_watermark_text || "",
      });
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: () => api.put("/settings/", form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
  });

  const uploadLogo = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post("/settings/logo/", fd).then((r) => r.data as AppSettings);
    },
    onSuccess: (data) => {
      setForm((f) => ({ ...f, pdf_logo_url: data.pdf_logo_url || "" }));
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  if (!isAdmin) return null;

  return (
    <div className="max-w-xl">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Настройки</h1>

      <div className="space-y-6 rounded-xl bg-white p-5 shadow-sm">
        <div>
          <label className="mb-1 block text-xs text-gray-500">Валюта по умолчанию</label>
          <select
            value={form.default_currency}
            onChange={(e) => setForm({ ...form, default_currency: e.target.value })}
            className="w-full rounded-lg border px-3 py-2 text-sm"
          >
            {SUPPORTED_CURRENCIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-400">
            Подставляется при создании новых работ и сделок. Курс не применяется — каждая цена хранит свою валюту.
          </p>
        </div>

        <div>
          <label className="mb-1 block text-xs text-gray-500">Название галереи (в PDF)</label>
          <input
            value={form.gallery_name}
            onChange={(e) => setForm({ ...form, gallery_name: e.target.value })}
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Артотека"
          />
        </div>

        <div className="border-t pt-5">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">PDF для клиента</h2>
          <label className="mb-1 block text-xs text-gray-500">Логотип галереи</label>
          {form.pdf_logo_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={imageUrl(form.pdf_logo_url)} alt="логотип" className="mb-2 max-h-16 rounded border bg-white p-1" />
          )}
          <div className="flex items-center gap-2">
            <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
              {uploadLogo.isPending ? "Загружаю…" : "Загрузить файл (PNG/JPG)"}
              <input
                type="file"
                accept="image/png,image/jpeg"
                className="hidden"
                disabled={uploadLogo.isPending}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadLogo.mutate(file);
                  e.target.value = "";
                }}
              />
            </label>
            {form.pdf_logo_url && (
              <button type="button" onClick={() => setForm({ ...form, pdf_logo_url: "" })} className="text-xs text-gray-400 hover:text-red-600">убрать</button>
            )}
          </div>
          <p className="mt-1 text-xs text-gray-400">Показывается в шапке PDF для клиента. Лучше загружать файлом — внешние ссылки (в т.ч. Google&nbsp;Drive) могут не подтягиваться. «Убрать» сохранится при нажатии «Сохранить».</p>

          <label className="mt-4 flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.pdf_watermark_enabled}
              onChange={(e) => setForm({ ...form, pdf_watermark_enabled: e.target.checked })}
            />
            Водяной знак на PDF
          </label>
          {form.pdf_watermark_enabled && (
            <input
              value={form.pdf_watermark_text}
              onChange={(e) => setForm({ ...form, pdf_watermark_text: e.target.value })}
              className="mt-2 w-full rounded-lg border px-3 py-2 text-sm"
              placeholder="Текст водяного знака (по умолчанию — название галереи)"
            />
          )}
        </div>

        <div className="flex items-center gap-3 border-t pt-5">
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Сохраняю…" : "Сохранить"}
          </button>
          {saved && <span className="text-sm text-green-600">Сохранено</span>}
        </div>
      </div>
    </div>
  );
}
