import { ogCard, OG_SIZE } from "../../../../components/og-card";
import { hours, monthLabel, wt } from "../../../../lib/wrapped";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = "image/png";
export const alt = "Seismo Wrapped";

const API = process.env.API_INTERNAL_URL || "http://api:8000";

export default async function Image({ params }) {
  const { locale, world } = await params;
  const t = wt(locale);
  const name = decodeURIComponent(world);
  const r = await fetch(`${API}/v1/wrapped-world/${encodeURIComponent(name)}`, { cache: "no-store" });
  const d = r.ok ? await r.json() : null;
  const nf = new Intl.NumberFormat(locale === "en" ? "en-GB" : "pt-BR");
  return ogCard({
    kicker: `SEISMO WRAPPED · ${d ? monthLabel(d.month, locale).toUpperCase() : ""}`,
    title: d ? d.world : name,
    subtitle: t.world,
    stats: d ? [[nf.format(d.avg_online || 0), t.avg_online], [nf.format(d.peak || 0), t.peak],
                [nf.format(d.deaths || 0), t.deaths], [`+${nf.format(d.levels_gained || 0)}`, t.world_levels]] : [],
  });
}
