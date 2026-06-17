const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function imageUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_URL}${path}`;
}

// Уменьшенное превью (для списков/каталога) — бэкенд отдаёт ресайз и кэширует.
export function thumbUrl(path: string | null | undefined, width = 400): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_URL}${path}?w=${width}`;
}
