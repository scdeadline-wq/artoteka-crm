"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STYLES = [
  { id: "living", name: "Гостиная" },
  { id: "office", name: "Кабинет" },
];

export default function ArtworkMockup({ artworkId }: { artworkId: number }) {
  const [activeStyle, setActiveStyle] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errored, setErrored] = useState(false);
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const start = (styleId: string) => {
    setActiveStyle(styleId);
    setLoading(true);
    setErrored(false);
  };

  const mockupUrl = activeStyle
    ? `${API_URL}/artworks/${artworkId}/mockup/?style=${activeStyle}&t=${token}`
    : null;

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        {STYLES.map((s) => (
          <button
            key={s.id}
            onClick={() => start(s.id)}
            className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              s.id === activeStyle
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {!activeStyle && <Sparkles size={12} />}
            {s.name}
          </button>
        ))}
      </div>

      <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-gray-100">
        {!activeStyle && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-400">
            Выберите стиль для генерации мокапа
          </div>
        )}
        {loading && activeStyle && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-100">
            <Loader2 size={24} className="animate-spin text-gray-400" />
          </div>
        )}
        {errored && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-100 px-4 text-center text-xs text-gray-500">
            Не удалось сгенерировать мокап. Попробуй ещё раз.
          </div>
        )}
        {mockupUrl && (
          <img
            key={activeStyle}
            src={mockupUrl}
            alt={`Мокап — ${STYLES.find((s) => s.id === activeStyle)?.name}`}
            className="h-full w-full object-contain"
            onLoad={() => setLoading(false)}
            onError={() => {
              setLoading(false);
              setErrored(true);
            }}
          />
        )}
      </div>
    </div>
  );
}
