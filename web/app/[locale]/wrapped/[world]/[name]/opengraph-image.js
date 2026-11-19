import { ImageResponse } from "next/og";
import { hours, monthLabel, wt } from "../../../../../lib/wrapped";

export const runtime = "nodejs";
export const size = { width: 1200, height: 630 };
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
  const stats = d ? [
    [nf.format(hours(d.minutes)), t.hours],
    [nf.format(d.days_active), t.days],
    [`+${nf.format(d.levels_gained)}`, t.levels],
    ...(d.top_percent ? [[`top ${d.top_percent}%`, t.top]] : []),
  ] : [];
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between",
                    padding: 64, background: "#151a19", color: "#e4ebe8" }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: 26, color: "#ff6b5e", letterSpacing: 4 }}>
            {`SEISMO WRAPPED · ${d ? monthLabel(d.month, locale).toUpperCase() : ""}`}
          </div>
          <div style={{ display: "flex", fontSize: 84, fontWeight: 700, marginTop: 12 }}>{d ? d.name : decodeURIComponent(name)}</div>
          <div style={{ display: "flex", fontSize: 30, color: "#9aa7a2", marginTop: 6 }}>
            {d ? `${d.vocation} · level ${d.level} · ${d.world}` : decodeURIComponent(world)}
          </div>
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          {stats.map(([v, l]) => (
            <div key={l} style={{ display: "flex", flexDirection: "column", flex: 1, padding: 24, borderRadius: 10,
                                  background: "#1b2120", border: "2px solid #2e3836" }}>
              <div style={{ display: "flex", fontSize: 58, fontWeight: 700 }}>{v}</div>
              <div style={{ display: "flex", fontSize: 24, color: "#9aa7a2" }}>{l}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", height: 8, background: "#ff6b5e", borderRadius: 4 }} />
      </div>
    ),
    size,
  );
}
