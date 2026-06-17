"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Image,
  Users,
  Receipt,
  Palette,
  LogOut,
  UserCog,
  Boxes,
  Settings,
  Menu,
  X,
} from "lucide-react";
import { useAuthStore, isAdmin as isAdminRole } from "@/lib/store";

const NAV = [
  { href: "/dashboard", label: "Дашборд", icon: LayoutDashboard },
  { href: "/artworks", label: "Произведения", icon: Image },
  { href: "/artists", label: "Художники", icon: Palette },
  { href: "/clients", label: "Клиенты", icon: Users },
  { href: "/sales", label: "Продажи", icon: Receipt },
  { href: "/storage", label: "Хранение", icon: Boxes, adminOnly: true },
  { href: "/users", label: "Пользователи", icon: UserCog, adminOnly: true },
  { href: "/settings", label: "Настройки", icon: Settings, adminOnly: true },
  // { href: "/mockup", label: "Мокап", icon: Sofa },  // скрыто: image-модель недоступна (geo-блок)
];

export default function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const isAdmin = isAdminRole(user);
  const items = NAV.filter((it) => !it.adminOnly || isAdmin);
  const [open, setOpen] = useState(false);

  // Закрывать мобильное меню при переходе на другую страницу.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const doLogout = () => {
    logout();
    window.location.href = "/login";
  };

  const navLinks = (
    <>
      {items.map(({ href, label, icon: Icon }) => {
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
    </>
  );

  const logoutBtn = (
    <button
      onClick={doLogout}
      className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
    >
      <LogOut size={18} />
      Выйти
    </button>
  );

  return (
    <>
      {/* Мобильный топ-бар с гамбургером */}
      <div className="flex items-center justify-between border-b bg-white px-4 py-3 md:hidden">
        <h1 className="text-lg font-bold text-gray-900">Артотека</h1>
        <button
          onClick={() => setOpen(true)}
          aria-label="Открыть меню"
          className="rounded-lg p-2 text-gray-600 hover:bg-gray-100"
        >
          <Menu size={22} />
        </button>
      </div>

      {/* Мобильное выезжающее меню */}
      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col border-r bg-white shadow-xl">
            <div className="flex items-center justify-between px-5 py-6">
              <h1 className="text-xl font-bold text-gray-900">Артотека</h1>
              <button
                onClick={() => setOpen(false)}
                aria-label="Закрыть меню"
                className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100"
              >
                <X size={20} />
              </button>
            </div>
            <nav className="flex-1 space-y-1 px-3">{navLinks}</nav>
            <div className="border-t p-3">{logoutBtn}</div>
          </aside>
        </div>
      )}

      {/* Десктопный сайдбар */}
      <aside className="hidden h-screen w-56 flex-col border-r bg-white md:flex">
        <div className="px-5 py-6">
          <h1 className="text-xl font-bold text-gray-900">Артотека</h1>
        </div>
        <nav className="flex-1 space-y-1 px-3">{navLinks}</nav>
        <div className="border-t p-3">{logoutBtn}</div>
      </aside>
    </>
  );
}
