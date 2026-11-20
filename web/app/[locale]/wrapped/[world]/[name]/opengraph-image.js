import { ogCard, OG_SIZE } from "../../../../../components/og-card";
import { hours, monthLabel, wt } from "../../../../../lib/wrapped";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = "image/png";
export const alt = "Seismo Wrapped";

const API = process.env.API_INTERNAL_URL || "http://api:8000";

// Cartão para compartilhar: aparece sozinho quando o link é colado no Discord, WhatsApp etc.
export default async function Image({ params }) {
  const { locale, world, name } = await params;
  const t = wt(locale);
  const r = await fetch(`${API}/v1/wrapped/${encodeURIComponent(decodeURIComponent(world))}/${encodeURIComponent(decodeURIComponent(name))}`, { cache: "no-store" });
  const d = r.ok ? await r.json() : null;
  const nf = new Intl.NumberFormat(locale === "en" ? "en-GB" : "pt-BR");
  return ogCard({
    kicker: `SEISMO WRAPPED · ${d ? monthLabel(d.month, locale).toUpperCase() : ""}`,
    title: d ? d.name : decodeURIComponent(name),
    subtitle: d ? `${d.vocation} · level ${d.level} · ${d.world}` : decodeURIComponent(world),
    stats: d ? [
      [nf.format(hours(d.minutes)), t.hours],
      [nf.format(d.days_active), t.days],
      [`+${nf.format(d.levels_gained)}`, t.levels],
      ...(d.top_percent ? [[`top ${d.top_percent}%`, t.top]] : []),
    ] : [],
  });
}
