import { notFound } from "next/navigation";
import { api, enc, fmtDate, fmtNum } from "../../../../../lib/api";
import { fmt } from "../../../../../lib/i18n";

export const dynamic = "force-dynamic";

const T = {
  pt: {
    title: "Mapa de hunts",
    back: "voltar ao mundo",
    lead: "Onde mais se caçou em {world} no dia {day}. As kill statistics dizem quantas criaturas morreram, não onde; cada área da TibiaWiki lista as criaturas que vivem lá, e as mortes de cada criatura são divididas entre as áreas onde ela vive. É uma estimativa.",
    day: "Dia",
    rank: "Ranking do dia",
    hunt: "Área de caça",
    city: "Cidade",
    kills: "Mortes (estimativa)",
    top: "Principais criaturas",
    floor: "andar",
    underground: "subsolo",
    empty: "Ainda não há kill statistics para este mundo.",
    note: "Círculos maiores = mais mortes. Áreas subterrâneas aparecem na posição da entrada, sobre o mapa da superfície.",
    credit: "Áreas de caça: TibiaWiki (CC BY-SA). Mapa: TibiaMaps (tibiamaps.io), mapa do jogo © CipSoft GmbH.",
  },
  en: {
    title: "Hunt map",
    back: "back to the world",
    lead: "Where people hunted the most in {world} on {day}. Kill statistics say how many creatures died, not where; each TibiaWiki area lists the creatures living there, and each creature's kills are split across the areas where it lives. It is an estimate.",
    day: "Day",
    rank: "Daily ranking",
    hunt: "Hunting area",
    city: "City",
    kills: "Kills (estimate)",
    top: "Main creatures",
    floor: "floor",
    underground: "underground",
    empty: "No kill statistics for this world yet.",
    note: "Bigger circles = more kills. Underground areas are drawn at their entrance, on the surface map.",
    credit: "Hunting areas: TibiaWiki (CC BY-SA). Map: TibiaMaps (tibiamaps.io), game map © CipSoft GmbH.",
  },
};

export async function generateMetadata({ params }) {
  const { world } = await params;
  return { title: `Hunts · ${decodeURIComponent(world)}` };
}

export default async function Hunts({ params, searchParams }) {
  const { locale, world } = await params;
  const sp = await searchParams;
  const t = T[locale] || T.pt;
  const day = /^\d{4}-\d{2}-\d{2}$/.test(sp.day || "") ? sp.day : "";
  const d = await api(`/v1/worlds/${enc(decodeURIComponent(world))}/hunts${day ? `?day=${day}` : ""}`);
  if (!d) notFound();
  const base = `/${locale}/world/${enc(d.world)}`;
  const { x_min, y_min, width, height } = d.bounds;
  const max = Math.max(1, ...d.hunts.map((h) => h.kills));
  const radius = (k) => 10 + 70 * Math.sqrt(k / max);
  const labels = new Set(d.hunts.slice(0, 12).map((h) => h.slug));
  const nf = (n) => fmtNum(n, locale);
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={base}>← {t.back}</a></p>
        <h1>{t.title} · {d.world}</h1>
        {d.day ? <p className="lead">{fmt(t.lead, { world: d.world, day: fmtDate(d.day, locale) })}</p> : <p className="lead">{t.empty}</p>}
        {d.days.length > 1 && (
          <p className="muted">
            {t.day}:{" "}
            {d.days.slice(0, 10).map((x) => (
              <a key={x} href={`${base}/hunts?day=${x}`} style={{ marginRight: 10, fontWeight: x === d.day ? 700 : 400 }}>{fmtDate(x, locale)}</a>
            ))}
          </p>
        )}
      </section>

      {d.hunts.length > 0 && (
        <section className="card">
          <div className="huntmap">
            <img src="/map-floor-07.png" alt="" width={width} height={height} />
            <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t.title}>
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
            <thead><tr><th>#</th><th>{t.hunt}</th><th>{t.city}</th><th className="n">{t.kills}</th><th>{t.top}</th></tr></thead>
            <tbody>
              {d.hunts.slice(0, 40).map((h, i) => (
                <tr key={h.slug}>
                  <td>{i + 1}</td>
                  <td>{h.name}{h.z !== 7 && <span className="muted"> · {t.underground}</span>}</td>
                  <td>{h.city || "–"}</td>
                  <td className="n">{nf(h.kills)}</td>
                  <td className="muted" style={{ whiteSpace: "normal" }}>{(h.top || []).map((c) => c.creature).join(", ")}</td>
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
