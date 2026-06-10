"use client";

import { useEffect, useState } from "react";

/** Возвращает значение с задержкой (debounce), чтобы не дёргать API на каждый символ. */
export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
