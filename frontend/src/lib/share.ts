export function shareUrl(token: string): string {
  return `${window.location.origin}/s/${token}`;
}

// navigator.clipboard работает только на HTTPS/localhost — на голом IP падаем в execCommand
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {}
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {}
  document.body.removeChild(ta);
  return ok;
}

export function worksLabel(n: number): string {
  const m10 = n % 10;
  const m100 = n % 100;
  const word =
    m10 === 1 && m100 !== 11 ? "работа" : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? "работы" : "работ";
  return `${n} ${word}`;
}
