"use client";

import { useState } from "react";
import { imageUrl } from "@/lib/image";

interface Room {
  name: string;
  wall: string;
  floor: string;
  furniture: React.ReactNode;
  accent?: string;
}

const ROOMS: Room[] = [
  {
    name: "Минимализм",
    wall: "bg-[#f5f0eb]",
    floor: "bg-[#c4a882]",
    furniture: (
      <>
        {/* Диван */}
        <div className="absolute bottom-[12%] left-1/2 -translate-x-1/2 w-[60%] h-[14%] rounded-t-lg bg-[#e8e0d6] shadow-md" />
        <div className="absolute bottom-[11%] left-1/2 -translate-x-1/2 w-[62%] h-[3%] rounded-sm bg-[#d4c9bb]" />
        {/* Подушки */}
        <div className="absolute bottom-[18%] left-[26%] w-[8%] h-[7%] rounded-sm bg-[#c9bfb2] rotate-[-5deg]" />
        <div className="absolute bottom-[18%] right-[26%] w-[8%] h-[7%] rounded-sm bg-[#bfb5a5] rotate-[3deg]" />
      </>
    ),
  },
  {
    name: "Лофт",
    wall: "bg-gradient-to-b from-[#8b7355] via-[#9c8465] to-[#a08b72]",
    floor: "bg-[#4a4035]",
    accent: "shadow-[0_4px_20px_rgba(0,0,0,0.5)]",
    furniture: (
      <>
        {/* Кирпичная текстура */}
        <div className="absolute inset-0 opacity-[0.15]"
          style={{
            backgroundImage: `repeating-linear-gradient(
              0deg, transparent, transparent 24px, rgba(0,0,0,0.15) 24px, rgba(0,0,0,0.15) 25px
            ), repeating-linear-gradient(
              90deg, transparent, transparent 48px, rgba(0,0,0,0.1) 48px, rgba(0,0,0,0.1) 49px
            )`,
          }}
        />
        {/* Столик */}
        <div className="absolute bottom-[12%] left-[20%] w-[16%] h-[1.5%] bg-[#2a2420] rounded-sm" />
        <div className="absolute bottom-[5%] left-[24%] w-[1%] h-[7%] bg-[#1a1815]" />
        <div className="absolute bottom-[5%] left-[33%] w-[1%] h-[7%] bg-[#1a1815]" />
        {/* Лампа */}
        <div className="absolute bottom-[13%] left-[25%] w-[5%] h-[12%] flex flex-col items-center">
          <div className="w-[60%] h-[40%] bg-[#f5e6c8] rounded-full opacity-90 shadow-[0_0_20px_rgba(245,230,200,0.4)]" />
          <div className="w-[8%] flex-1 bg-[#2a2420]" />
        </div>
      </>
    ),
  },
  {
    name: "Классика",
    wall: "bg-[#e8ddd0]",
    floor: "bg-[#6b5a4e]",
    furniture: (
      <>
        {/* Молдинг верх */}
        <div className="absolute top-0 left-0 right-0 h-[3%] bg-[#d4c9bb] shadow-sm" />
        {/* Молдинг низ */}
        <div className="absolute bottom-[22%] left-0 right-0 h-[1.5%] bg-[#d4c9bb]" />
        {/* Комод */}
        <div className="absolute bottom-[12%] right-[15%] w-[22%] h-[10%] rounded-t-sm bg-[#5c4a3a]" />
        <div className="absolute bottom-[11%] right-[14%] w-[24%] h-[1.5%] bg-[#4a3a2d]" />
        {/* Ваза */}
        <div className="absolute bottom-[22%] right-[22%] w-[4%] h-[8%] rounded-full bg-[#c4a882] opacity-80" />
      </>
    ),
  },
  {
    name: "Скандинавский",
    wall: "bg-white",
    floor: "bg-[#d4c4a8]",
    furniture: (
      <>
        {/* Кресло */}
        <div className="absolute bottom-[12%] right-[20%] w-[18%] h-[15%] rounded-t-2xl bg-[#e0d5c5]" />
        <div className="absolute bottom-[8%] right-[21%] w-[4%] h-[5%] bg-[#b5a48e] rounded-sm rotate-[-8deg]" />
        <div className="absolute bottom-[8%] right-[22.5%] w-[4%] h-[5%] bg-[#b5a48e] rounded-sm rotate-[8deg]" />
        {/* Растение */}
        <div className="absolute bottom-[12%] left-[12%] w-[6%] h-[4%] rounded-t-sm bg-[#d4c4a8]" />
        <div className="absolute bottom-[16%] left-[10%] w-[10%] h-[14%] rounded-full bg-[#7a9b6d] opacity-70" />
      </>
    ),
  },
];

export default function ArtworkMockup({
  imageSrc,
  title,
}: {
  imageSrc: string;
  title?: string;
}) {
  const [activeRoom, setActiveRoom] = useState(0);
  const room = ROOMS[activeRoom];
  const src = imageUrl(imageSrc);

  return (
    <div>
      {/* Переключатель стилей */}
      <div className="mb-3 flex gap-2">
        {ROOMS.map((r, i) => (
          <button
            key={r.name}
            onClick={() => setActiveRoom(i)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              i === activeRoom
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {r.name}
          </button>
        ))}
      </div>

      {/* Мокап */}
      <div
        className={`relative aspect-[16/10] overflow-hidden rounded-xl ${room.wall}`}
      >
        {/* Мебель и декор (за картиной) */}
        {room.furniture}

        {/* Пол */}
        <div
          className={`absolute bottom-0 left-0 right-0 h-[22%] ${room.floor}`}
        />
        <div className="absolute bottom-[21.5%] left-0 right-0 h-[1px] bg-black/10" />

        {/* Картина на стене */}
        <div className="absolute top-[15%] left-1/2 -translate-x-1/2 flex flex-col items-center"
          style={{ width: "35%" }}
        >
          {/* Тень за рамой */}
          <div
            className={`absolute -inset-[3%] bg-black/20 blur-md rounded-sm ${room.accent || ""}`}
          />
          {/* Рама */}
          <div className="relative border-[3px] border-[#3a3028] bg-white p-[2px] shadow-lg">
            <img
              src={src}
              alt={title || ""}
              className="relative block w-full"
              style={{ maxHeight: "280px", objectFit: "contain" }}
            />
          </div>
        </div>

        {/* Свет сверху (имитация) */}
        <div
          className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-[50%] h-[60%] opacity-[0.08]"
          style={{
            background:
              "radial-gradient(ellipse at top, white 0%, transparent 70%)",
          }}
        />
      </div>
    </div>
  );
}
