// Chamadas à API feitas no servidor (rede interna do Docker). O navegador nunca fala com a API direto.
const API = process.env.API_INTERNAL_URL || "http://api:8000";

export async function api(path) {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`API ${path} respondeu ${r.status}`);
  return r.json();
}

export const enc = encodeURIComponent;

const NUM = { pt: "pt-BR", en: "en-GB" };
const ZONE = { pt: "America/Sao_Paulo", en: "Europe/Berlin" };

export function fmtNum(n, locale = "pt") {
  return n == null ? "–" : new Intl.NumberFormat(NUM[locale]).format(n);
}

export function fmtTime(iso, locale = "pt") {
  if (!iso) return "–";
  return new Intl.DateTimeFormat(NUM[locale], { dateStyle: "short", timeStyle: "short", timeZone: ZONE[locale] })
    .format(new Date(iso));
}

export function fmtDate(iso, locale = "pt") {
  if (!iso) return "–";
  const d = iso.length === 10 ? new Date(`${iso}T12:00:00Z`) : new Date(iso);
  return new Intl.DateTimeFormat(NUM[locale], { dateStyle: "medium", timeZone: "UTC" }).format(d);
}
