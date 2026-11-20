import { ogCard, OG_SIZE } from "../../../../../../components/og-card";
import { hours, monthLabel, wt } from "../../../../../../lib/wrapped";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = "image/png";
export const alt = "Seismo Wrapped";

const API = process.env.API_INTERNAL_URL || "http://api:8000";

export default async function Image({ params }) {
  const { locale, world, guild } = await params;
  const t = wt(locale);
  const r = await fetch(`${API}/v1/wrapped-guild/${encodeURIComponent(decodeURIComponent(world))}/${encodeURIComponent(decodeURIComponent(guild))}`, { cache: "no-store" });
  const d = r.ok ? await r.json() : null;
  const nf = new Intl.NumberFormat(locale === "en" ? "en-GB" : "pt-BR");
  return ogCard({
    kicker: `SEISMO WRAPPED · ${d ? monthLabel(d.month, locale).toUpperCase() : ""}`,
    title: d ? d.guild : decodeURIComponent(guild),
    subtitle: d ? `${t.guild} · ${d.world}` : t.guild,
    stats: d ? [[nf.format(d.members_total || 0), t.members], [nf.format(d.active_members || 0), t.active],
                [nf.format(hours(d.minutes)), t.member_hours], [`+${nf.format(d.levels_gained || 0)}`, t.levels]] : [],
  });
}
