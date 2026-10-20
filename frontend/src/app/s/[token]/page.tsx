"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { imageUrl, thumbUrl } from "@/lib/image";
import { formatPrice } from "@/lib/currency";
import { worksLabel } from "@/lib/share";
import type { PublicArtwork, PublicShare } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function sizeLabel(a: PublicArtwork): string | null {
  // принято: высота × ширина
  if (a.height_cm && a.width_cm) return `${a.height_cm} × ${a.width_cm} см`;
  if (a.height_cm) return `${a.height_cm} см (в)`;
  if (a.width_cm) return `${a.width_cm} см (ш)`;
  return null;
}

// Публичная страница подборки — без авторизации, открывается клиентом по ссылке.
export default function PublicSharePage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<PublicShare | null>(null);
  const [error, setError] = useState(false);
  const [open, setOpen] = useState<PublicArtwork | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/public/shares/${encodeURIComponent(token)}/`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => setError(true));
  }, [token]);

  useEffect(() => {
    if (data) document.title = data.title;
  }, [data]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 text-center text-gray-500">
        Подборка не найдена или ссылка больше не действует.
      </div>
    );
  }
  if (!data) {
    return <div className="flex min-h-screen items-center justify-center text-gray-400">Загрузка…</div>;
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="mx-auto max-w-6xl px-4 pb-6 pt-10 sm:px-6">
        <p className="text-xs uppercase tracking-widest text-gray-400">Подборка работ</p>
        <h1 className="mt-1 text-2xl font-semibold text-gray-900 sm:text-3xl">{data.title}</h1>
        <p className="mt-1 text-sm text-gray-500">{worksLabel(data.artworks.length)}</p>
      </header>

      <main className="mx-auto grid max-w-6xl grid-cols-1 gap-x-6 gap-y-10 px-4 pb-16 sm:grid-cols-2 sm:px-6 lg:grid-cols-3">
        {data.artworks.length === 0 && <p className="text-gray-500">Пока здесь нет работ.</p>}
        {data.artworks.map((a) => (
          <button key={a.id} onClick={() => setOpen(a)} className="group block w-full min-w-0 text-left">
            <div className="flex aspect-[4/5] w-full items-center justify-center overflow-hidden bg-gray-50">
              {a.images[0] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={thumbUrl(a.images[0], 800)}
                  alt={a.title || ""}
                  loading="lazy"
                  className="max-h-full max-w-full object-contain transition-transform duration-300 group-hover:scale-[1.02]"
                />
              ) : (
                <span className="text-sm text-gray-300">Нет фото</span>
              )}
            </div>
            <ArtworkCaption a={a} showPrices={data.show_prices} />
          </button>
        ))}
      </main>

      {open && <ArtworkModal a={open} showPrices={data.show_prices} onClose={() => setOpen(null)} />}
    </div>
  );
}

function ArtworkCaption({ a, showPrices }: { a: PublicArtwork; showPrices: boolean }) {
  const meta = [a.techniques.join(", "), sizeLabel(a)].filter(Boolean).join(" · ");
  return (
    <div className="mt-3 space-y-0.5">
      <p className="text-sm font-medium text-gray-900">{a.artist_name}</p>
      <p className="text-sm text-gray-700">
        <span className="italic">{a.title || "Без названия"}</span>
        {a.year ? `, ${a.year}` : ""}
      </p>
      {meta && <p className="text-xs text-gray-500">{meta}</p>}
      {a.is_reserved ? (
        <p className="text-xs text-blue-700">В резерве</p>
      ) : (
        showPrices && a.sale_price && <p className="text-sm text-gray-900">{formatPrice(a.sale_price, a.currency)}</p>
      )}
    </div>
  );
}

function ArtworkModal({ a, showPrices, onClose }: { a: PublicArtwork; showPrices: boolean; onClose: () => void }) {
  const [idx, setIdx] = useState(0);
  const count = a.images.length;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") setIdx((i) => (i + 1) % Math.max(count, 1));
      if (e.key === "ArrowLeft") setIdx((i) => (i - 1 + count) % Math.max(count, 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [count, onClose]);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-white">
      <button onClick={onClose} className="fixed right-4 top-4 z-10 rounded-full bg-white/90 p-2 text-gray-600 shadow hover:text-gray-900">
        <X size={22} />
      </button>
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_320px]">
        <div>
          <div className="relative flex h-[60vh] items-center justify-center bg-gray-50 sm:h-[75vh]">
            {count > 0 ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={imageUrl(a.images[idx])} alt={a.title || ""} className="max-h-full max-w-full object-contain" />
            ) : (
              <span className="text-gray-300">Нет фото</span>
            )}
            {count > 1 && (
              <>
                <button onClick={() => setIdx((idx - 1 + count) % count)} className="absolute left-2 rounded-full bg-white/80 p-2 shadow">
                  <ChevronLeft size={20} />
                </button>
                <button onClick={() => setIdx((idx + 1) % count)} className="absolute right-2 rounded-full bg-white/80 p-2 shadow">
                  <ChevronRight size={20} />
                </button>
              </>
            )}
          </div>
          {count > 1 && (
            <div className="mt-3 flex gap-2 overflow-x-auto">
              {a.images.map((img, i) => (
                <button key={img} onClick={() => setIdx(i)} className={`h-16 w-16 shrink-0 border-2 ${i === idx ? "border-gray-900" : "border-transparent"}`}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={thumbUrl(img, 160)} alt="" className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
        <div>
          <ArtworkCaption a={a} showPrices={showPrices} />
          {a.is_framed && <p className="mt-1 text-xs text-gray-500">В раме</p>}
          {a.description && <p className="mt-4 whitespace-pre-line text-sm leading-relaxed text-gray-700">{a.description}</p>}
        </div>
      </div>
    </div>
  );
}
