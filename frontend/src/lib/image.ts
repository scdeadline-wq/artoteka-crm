const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function imageUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_URL}${path}`;
}
