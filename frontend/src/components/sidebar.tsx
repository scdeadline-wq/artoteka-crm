"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Image,
  Users,
  Receipt,
  Palette,
  LogOut,
} from "lucide-react";
import { useAuthStore } from "@/lib/store";

const NAV = [
  { href: "/dashboard", label: "Дашборд", icon: LayoutDashboard },
  { href: "/artworks", label: "Произведения", icon: Image },
  { href: "/artists", label: "Художники", icon: Palette },
  { href: "/clients", label: "Клиенты", icon: Users },
  { href: "/sales", label: "Продажи", icon: Receipt },
];

export default function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);

  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-white">
      <div className="px-5 py-6">
        <h1 className="text-xl font-bold text-gray-900">Артотека</h1>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-gray-100 text-gray-900"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t p-3">
        <button
          onClick={() => {
            logout();
            window.location.href = "/login";
          }}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
        >
          <LogOut size={18} />
          Выйти
        </button>
      </div>
    </aside>
  );
}
