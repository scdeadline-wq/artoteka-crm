"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Loader2, X, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore, isAdmin as isAdminRole, isOwner as isOwnerRole, type UserRole } from "@/lib/store";

interface UserRow {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  created_at: string;
}

const ROLE_LABEL: Record<UserRole, string> = {
  owner: "Owner",
  admin: "Admin",
  manager: "Manager",
  viewer: "Viewer",
};

export default function UsersPage() {
  const router = useRouter();
  const me = useAuthStore((s) => s.user);
  const canAccess = isAdminRole(me);
  const meIsOwner = isOwnerRole(me);
  const queryClient = useQueryClient();
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    if (me && !canAccess) router.replace("/artworks");
  }, [me, canAccess, router]);

  const { data: users = [], isLoading } = useQuery<UserRow[]>({
    queryKey: ["users"],
    queryFn: () => api.get("/users/").then((r) => r.data),
    enabled: canAccess,
  });

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "viewer" as UserRole,
  });

  const create = useMutation({
    mutationFn: () => api.post("/users/", form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setForm({ name: "", email: "", password: "", role: "viewer" });
      setShowForm(false);
      setErrMsg(null);
    },
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось создать пользователя");
    },
  });

  const updateRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: UserRole }) =>
      api.put(`/users/${id}/`, { role }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось сменить роль");
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/users/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
    onError: (e: { response?: { data?: { detail?: string } } }) => {
      setErrMsg(e?.response?.data?.detail || "Не удалось удалить");
    },
  });

  if (!canAccess) return null;

  // Доступные роли при создании / смене:
  // - admin (не owner) не может ставить роль owner
  const assignableRoles: UserRole[] = meIsOwner
    ? ["owner", "admin", "manager", "viewer"]
    : ["admin", "manager", "viewer"];

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-1 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Пользователи</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          <Plus size={14} /> Пригласить
        </button>
      </div>
      <p className="mb-6 text-sm text-gray-500">
        Owner — полный доступ. Admin — то же, кроме назначения роли owner.
        Manager/Viewer — только просмотр (не видят закупочные цены).
      </p>

      {errMsg && (
        <div className="mb-4 flex items-center justify-between rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          <span>{errMsg}</span>
          <button onClick={() => setErrMsg(null)} aria-label="Закрыть">
            <X size={14} />
          </button>
        </div>
      )}

      {showForm && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!form.name.trim() || !form.email.trim() || !form.password) return;
            create.mutate();
          }}
          className="mb-6 grid grid-cols-1 gap-3 rounded-xl bg-white p-4 shadow-sm sm:grid-cols-2"
        >
          <div>
            <label className="mb-1 block text-xs text-gray-500">Имя</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full rounded-lg border px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">
              Временный пароль (передашь пользователю)
            </label>
            <input
              type="text"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              minLength={6}
              className="w-full rounded-lg border px-3 py-2 text-sm font-mono"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Роль</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
              className="w-full rounded-lg border px-3 py-2 text-sm"
            >
              {assignableRoles.map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABEL[r]}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={create.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {create.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              Создать
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <p className="text-gray-500">Загрузка...</p>
      ) : (
        <div className="overflow-hidden rounded-xl bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-gray-500">
                <th className="px-4 py-3">Имя</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3 w-40">Роль</th>
                <th className="px-4 py-3 w-24 text-right"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isMe = u.id === me?.id;
                const isOtherOwner = u.role === "owner" && !isMe;
                // Менять чужого owner / снимать owner может только owner
                const roleEditable = !isOtherOwner || meIsOwner;
                // Опции в селекте: admin не может выставить owner; owner для текущей строки разрешён только если можно его трогать
                const roleOptions: UserRole[] = (
                  meIsOwner
                    ? ["owner", "admin", "manager", "viewer"]
                    : ["admin", "manager", "viewer"]
                ) as UserRole[];
                // Удалять нельзя себя и (для не-owner) — owner
                const canDelete = !isMe && (meIsOwner || u.role !== "owner");
                return (
                  <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{u.name}</span>
                        {isMe && (
                          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] uppercase text-blue-700">
                            вы
                          </span>
                        )}
                        {u.role === "owner" && (
                          <ShieldCheck size={14} className="text-amber-500" />
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">{u.email}</td>
                    <td className="px-4 py-2.5">
                      <select
                        value={u.role}
                        disabled={!roleEditable || updateRole.isPending}
                        onChange={(e) => {
                          const role = e.target.value as UserRole;
                          if (role === u.role) return;
                          updateRole.mutate({ id: u.id, role });
                        }}
                        className="w-full rounded border px-2 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {roleOptions.map((r) => (
                          <option key={r} value={r}>{ROLE_LABEL[r]}</option>
                        ))}
                        {/* Если текущая роль не в списке доступных (например owner для admin) — показываем её отключённой */}
                        {!roleOptions.includes(u.role) && (
                          <option value={u.role} disabled>{ROLE_LABEL[u.role]}</option>
                        )}
                      </select>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {canDelete && (
                        <button
                          onClick={() => {
                            if (!confirm(`Удалить пользователя «${u.name}»?`)) return;
                            remove.mutate(u.id);
                          }}
                          disabled={remove.isPending}
                          className="rounded p-1.5 text-red-600 hover:bg-red-50 disabled:opacity-30"
                          aria-label="Удалить"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
