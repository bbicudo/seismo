// sitemap.xml com as páginas públicas em português e inglês (cada uma com o par no outro idioma).
// Perfis de personagem e páginas de casa ficam de fora de propósito (privacidade e volume).
export const dynamic = "force-dynamic";
export const revalidate = 3600;

const API = process.env.API_INTERNAL_URL || "http://api:8000";
const enc = encodeURIComponent;

import { getParams } from "../lib/flags";

export default async function sitemap() {
  const base = process.env.PUBLIC_URL || "http://localhost:3000";
  let d = { flags: {}, worlds: [], guilds: [], towns: [] };
  try {
    const r = await fetch(`${API}/v1/sitemap`, { cache: "no-store" });
    if (r.ok) d = await r.json();
  } catch {}
  const p = await getParams();
  if (!p.seo_indexing) return [];
  const on = (k) => d.flags[k] !== false;
  const out = [];
  const add = (path, opts = {}) => {
    for (const locale of ["pt", "en"]) {
      out.push({
        url: `${base}/${locale}${path}`,
        lastModified: opts.lastModified ? new Date(opts.lastModified) : undefined,
        changeFrequency: opts.freq || "daily",
        priority: opts.priority ?? 0.5,
        alternates: { languages: { "pt-BR": `${base}/pt${path}`, en: `${base}/en${path}` } },
      });
    }
  };
  add("", { freq: "hourly", priority: 1 });
  if (on("page_events")) add("/events", { priority: 0.6 });
  if (on("page_wrapped")) add("/wrapped", { freq: "weekly", priority: 0.5 });
  add("/about", { freq: "monthly", priority: 0.3 });
  add("/privacy", { freq: "monthly", priority: 0.3 });
  add("/opt-out", { freq: "monthly", priority: 0.3 });
  for (const w of d.worlds) {
    const wp = `/world/${enc(w.name)}`;
    add(wp, { freq: "hourly", priority: 0.9, lastModified: w.updated_at });
    if (!p.seo_sitemap_worlds_extra) continue;
    if (on("page_hunts")) add(`${wp}/hunts`, { priority: 0.7 });
    if (on("page_raids")) add(`${wp}/raids`, { priority: 0.7 });
    if (on("page_wrapped")) add(`/wrapped/${enc(w.name)}`, { freq: "weekly", priority: 0.5 });
  }
  if (p.seo_sitemap_guilds) for (const g of d.guilds) add(`/world/${enc(g.world)}/guild/${enc(g.name)}`, { freq: "weekly", priority: 0.4, lastModified: g.updated_at });
  if (p.seo_sitemap_towns) for (const t of d.towns) add(`/world/${enc(t.world)}/town/${enc(t.town)}`, { priority: 0.4 });
  return out;
}
