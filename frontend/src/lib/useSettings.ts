import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { AppSettings } from "@/lib/types";
import { DEFAULT_CURRENCY } from "@/lib/currency";

// Настройки приложения (валюта по умолчанию, лого/водяной знак PDF).
// Кешируются надолго — меняются редко.
export function useSettings() {
  return useQuery<AppSettings>({
    queryKey: ["settings"],
    queryFn: () => api.get("/settings/").then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useDefaultCurrency(): string {
  const { data } = useSettings();
  return data?.default_currency || DEFAULT_CURRENCY;
}
