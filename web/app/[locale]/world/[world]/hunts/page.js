import { notFound } from "next/navigation";
import { api, enc, fmtDate, fmtNum } from "../../../../../lib/api";
import { getFlags, on } from "../../../../../lib/flags";
import { fmt } from "../../../../../lib/i18n";
import { it, signed, trendClass } from "../../../../../lib/insights-i18n";
import { D, seo } from "../../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale, world } = await params;
  const w = decodeURIComponent(world);
  return seo(locale, `/world/${encodeURIComponent(w)}/hunts`, { title: `Hunts · ${w}`, description: D.hunts[locale === "en" ? "en" : "pt"](w) });
}

export const dynamic = "force-dynamic";

const T = {
  pt: {
    day: "Dia", rank: "Ranking do dia", hunt: "Área de caça", city: "Cidade", kills: "Criaturas mortas (estimativa)",
    top: "Principais criaturas", underground: "subsolo", empty: "Ainda não há kill statistics para este mundo.",
    note: "Círculos maiores = mais mortes. Áreas subterrâneas aparecem na posição da entrada, sobre o mapa da superfície.",
    credit: "Áreas de caça: TibiaWiki (CC BY-SA). Mapa: TibiaMaps (tibiamaps.io), mapa do jogo © CipSoft GmbH.",
  },
  en: {
    day: "Day", rank: "Daily ranking", hunt: "Hunting area", city: "City", kills: "Creatures killed (estimate)",
    top: "Main creatures", underground: "underground", empty: "No kill statistics for this world yet.",
    note: "Bigger circles = more kills. Underground areas are drawn at their entrance, on the surface map.",
    credit: "Hunting areas: TibiaWiki (CC BY-SA). Map: TibiaMaps (tibiamaps.io), game map © CipSoft GmbH.",
  },
};

export default async function Hunts({ params, searchParams }) {
  const { locale, world } = await params;
  const sp = await searchParams;
  const t = T[locale] || T.pt;
  const x = it(locale);
  const day = /^\d{4}-\d{2}-\d{2}$/.test(sp.day || "") ? sp.day : "";
  const [d, f] = await Promise.all([api(`/v1/worlds/${enc(decodeURIComponent(world))}/hunts${day ? `?day=${day}` : ""}`), getFlags()]);
  if (!d) notFound();
  const base = `/${locale}/world/${enc(d.world)}`;
  const { x_min, y_min, width, height } = d.bounds;
  const max = Math.max(1, ...d.hunts.map((h) => h.kills));
  const radius = (k) => 4 + 72 * Math.sqrt(k / max);
  const labels = new Set(d.hunts.slice(0, 12).map((h) => h.slug));
  const nf = (n) => fmtNum(n, locale);
  // jogadores mortos (estimativa) com a proporção na dica: mais fácil de ler que "por mil"
  const deaths = (h) => (h.deaths == null ? <span className="muted">–</span>
    : <span title={h.deaths > 0 ? fmt(x.risk_tip, { n: nf(Math.round(h.kills / h.deaths)) }) : undefined}>{nf(h.deaths)}</span>);
  const trends = d.trends;
  const deltaHead = fmt(x.delta_days, { d: d.trend_days });
  return (
    <>
      <section className="card">
        <h2>{x.hunts_title}</h2>
        {d.day ? <p className="lead">{fmt(x.hunts_lead, { day: fmtDate(d.day, locale) })}</p> : <p className="lead">{t.empty}</p>}
        {d.days.length > 1 && (
          <p className="seg">
            {d.days.slice(0, 10).map((v) => (
              <a key={v} href={`${base}/hunts?day=${v}`} aria-current={v === d.day ? "true" : undefined}>{fmtDate(v, locale)}</a>
            ))}
          </p>
        )}
        {d.day && (
          <div className="stats">
            <div className="stat"><b>{nf(d.totals.killed)}</b><span>{x.creatures_killed}</span></div>
            {on(f, "page_kills") && <div className="stat"><b>{nf(d.totals.deaths)}</b><span>{x.players_killed_day}</span></div>}
          </div>
        )}
        {d.day && (
          <details className="how">
            <summary>{x.hunts_how}</summary>
            <p>{fmt(x.hunts_how_text, { d: d.trend_days })}</p>
            {trends && d.base_days < 3 && <p className="muted">{fmt(x.trend_wait, { n: d.base_days })}</p>}
          </details>
        )}
      </section>

      {d.hunts.length > 0 && (
        <section className="card">
          <div className="huntmap">
            <img src="/map-floor-07.png" alt="" width={width} height={height} />
            <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={x.hunts_title}>
              {[...d.hunts].reverse().map((h) => {
                const cx = h.x - x_min, cy = h.y - y_min, r = radius(h.kills);
                const tip = `${h.name}${h.city ? ` (${h.city})` : ""}: ${nf(h.kills)}\n` +
                  (h.top || []).map((c) => `${c.creature}: ${nf(c.part)}`).join("\n");
                return (
                  <g key={h.slug}>
                    <circle cx={cx} cy={cy} r={r} className={h.z === 7 ? "hunt" : "hunt under"}><title>{tip}</title></circle>
                    {labels.has(h.slug) && <text x={cx} y={cy - r - 8} className="hunt-label">{h.name}</text>}
                  </g>
                );
              })}
            </svg>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>{t.note}</p>
        </section>
      )}

      {d.hunts.length > 0 && (
        <section className="card">
          <h2>{t.rank}</h2>
          <div className="tbl"><table>
            <thead><tr>
              <th>#</th><th>{t.hunt}</th><th>{t.city}</th><th className="n">{t.kills}</th>
              {trends && <><th className="n">{deltaHead}</th><th className="n">{x.deaths_est}</th></>}
              <th>{t.top}</th>
            </tr></thead>
            <tbody>
              {d.hunts.slice(0, 40).map((h, i) => (
                <tr key={h.slug}>
                  <td>{i + 1}</td>
                  <td>{h.name}{h.z !== 7 && <span className="muted"> · {t.underground}</span>}</td>
                  <td>{h.city || "–"}</td>
                  <td className="n">{nf(h.kills)}</td>
                  {trends && <><td className={`n ${trendClass(h.delta_pct)}`}>{signed(h.delta_pct, locale)}</td><td className="n">{deaths(h)}</td></>}
                  <td className="muted wrap-cell">{(h.top || []).map((c) => c.creature).join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </section>
      )}

      {on(f, "page_kills") && d.creatures.length > 0 && (
        <section className="card">
          <h2>{x.creatures_day}</h2>
          <div className="tbl"><table>
            <thead><tr>
              <th>{x.creature}</th><th className="n">{x.killed}</th><th className="n">{x.players_killed}</th>
              {trends && <th className="n">{deltaHead}</th>}
            </tr></thead>
            <tbody>
              {d.creatures.map((c) => (
                <tr key={c.race}>
                  <td>{c.race}</td><td className="n">{nf(c.killed)}</td><td className="n">{nf(c.players_killed)}</td>
                  {trends && <td className={`n ${trendClass(c.delta_pct)}`}>{signed(c.delta_pct, locale)}</td>}
                </tr>
              ))}
            </tbody>
          </table></div>
        </section>
      )}
      <p className="muted">{t.credit}</p>
    </>
  );
}
