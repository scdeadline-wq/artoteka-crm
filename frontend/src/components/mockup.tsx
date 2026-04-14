"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STYLES = [
  { id: "living", name: "Гостиная" },
  { id: "office", name: "Кабинет" },
];

export default function ArtworkMockup({ artworkId }: { artworkId: number }) {
  const [activeStyle, setActiveStyle] = useState("living");
  const [loading, setLoading] = useState(true);
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const mockupUrl = `${API_URL}/artworks/${artworkId}/mockup/?style=${activeStyle}&t=${token}`;

  return (
    <div>
      <div className="mb-3 flex gap-2">
        {STYLES.map((s) => (
          <button
            key={s.id}
            onClick={() => {
              setActiveStyle(s.id);
              setLoading(true);
            }}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              s.id === activeStyle
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {s.name}
          </button>
        ))}
      </div>

      <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-gray-100">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-100">
            <Loader2 size={24} className="animate-spin text-gray-400" />
          </div>
        )}
        <img
          key={activeStyle}
          src={mockupUrl}
          alt={`Мокап — ${STYLES.find((s) => s.id === activeStyle)?.name}`}
          className="h-full w-full object-contain"
          onLoad={() => setLoading(false)}
          onError={() => setLoading(false)}
        />
      </div>
    </div>
  );
}
