import { TimeChart } from "../../components/charts";
import { api, enc, fmtDate, fmtNum } from "../../lib/api";
import { dict, fmt } from "../../lib/i18n";
import { it, signed, trendClass } from "../../lib/insights-i18n";
import { getFlags, on } from "../../lib/flags";
import CharacterSearch from "../../components/character-search";
import { D, seo } from "../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  return seo(locale, "", { title: t.overview_title, description: t.overview_lead });
}

export const dynamic = "force-dynamic";

export default async function Overview({ params, searchParams }) {
  const { locale } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const f = await getFlags();
  const x = it(locale);
  const [ov, all, ev, hl] = await Promise.all([
    api("/v1/overview"), api("/v1/worlds"),
    on(f, "page_events") ? api("/v1/events?past=0&ahead=7") : null,
    on(f, "page_health_index") ? api("/v1/insights/health") : null,
  ]);
  const region = sp.region || "";
  const pvp = sp.pvp || "";
  const health = new Map((hl?.worlds || []).map((w) => [w.name, w]));
  const showH = !!hl?.ready; // colunas só depois que o índice existe (antes disso seriam só traços)
  const sort = ["online", "health", "trend"].includes(sp.sort) && hl?.ready ? sp.sort : "online";
  const key = { online: (w) => w.players_online ?? -1, health: (w) => health.get(w.name)?.score ?? -1, trend: (w) => health.get(w.name)?.trend_pct ?? -1e9 }[sort];
  const worlds = all.filter((w) => (!region || w.location === region) && (!pvp || w.pvp_type === pvp))
    .sort((a, b) => key(b) - key(a) || a.name.localeCompare(b.name));
  const qs = (o) => { const q = new URLSearchParams({ ...(region && { region }), ...(pvp && { pvp }), ...o }); return `/${locale}?${q}#worlds`; };
  const total = all.reduce((s, w) => s + (w.players_online || 0), 0);
  const pvps = [...new Set(all.map((w) => w.pvp_type))].sort();
  const points = ov.series_48h.map((p) => ({ t: p.ts, v: p.players_online }));
  const peak48 = points.length ? Math.max(...points.map((p) => p.v)) : null;
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
        "@context": "https://schema.org", "@type": "WebSite", name: "Seismo",
        url: `${process.env.PUBLIC_URL || ""}/${locale}`, inLanguage: locale === "en" ? "en" : "pt-BR",
        description: t.overview_lead,
      }) }} />
      <section className="card hero">
        <h1>{t.overview_title}</h1>
        <p className="lead">{t.overview_lead}</p>
        {on(f, "page_characters") && <CharacterSearch locale={locale} />}
        <div className="stats">
          <div className="stat"><b>{fmtNum(total, locale)}</b><span>{t.players_online}</span></div>
          <div className="stat"><b>{fmtNum(all.length, locale)}</b><span>{t.worlds}</span></div>
          <div className="stat"><b>{fmtNum(peak48, locale)}</b><span>{t.peak} 48 h</span></div>
        </div>
      </section>

      {ev && on(f, "page_events") && <section className="card">
        <h2>{t.today_title}</h2>
        <div className="stats">
          <div className="stat"><b style={{ fontSize: 20 }}>{ev.boosted?.creature || "–"}</b><span>{t.boosted_creature}</span></div>
          <div className="stat"><b style={{ fontSize: 20 }}>{ev.boosted?.boss || "–"}</b><span>{t.boosted_boss}</span></div>
          <div className="stat"><b style={{ fontSize: ev.active.length ? 20 : 15, fontWeight: ev.active.length ? 600 : 400 }}>{ev.active.length ? ev.active.map((e) => e.name).join(", ") : t.no_events_today}</b><span>{t.active_events}</span></div>
        </div>
        <p className="muted" style={{ marginTop: 10 }}><a href={`/${locale}/events`}>{t.all_events} →</a></p>
      </section>}

      <div className={on(f, "page_kills") ? "grid2" : undefined}>
        <section className="card">
          <h2>{t.total_48h}</h2>
          <TimeChart points={points} locale={locale} label={t.total_48h} peakLabel={t.peak} />
        </section>
        {on(f, "page_kills") && (
          <section className="card">
            <h2>{t.top_deaths}</h2>
            {ov.top_deaths.length === 0 ? <p className="muted">{t.not_yet}</p> : (
              <>
                <p className="lead">{fmt(t.top_deaths_lead, { date: fmtDate(ov.top_deaths[0].stats_day, locale) })}</p>
                <div className="tbl">
                  <table>
                    <thead><tr><th>#</th><th>{t.world}</th><th className="n">{t.deaths}</th></tr></thead>
                    <tbody>
                      {ov.top_deaths.map((d, i) => (
                        <tr key={d.name}>
                          <td>{i + 1}</td>
                          <td><a href={`/${locale}/world/${enc(d.name)}/hunts`}>{d.name}</a></td>
                          <td className="n">{fmtNum(d.deaths, locale)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
        )}
      </div>

      <section className="card" id="worlds">
        <h2>{t.nav_worlds}</h2>
        <form className="filters" method="get">
          <label htmlFor="f-region">{t.region}
            <select id="f-region" name="region" defaultValue={region}>
              <option value="">{t.filter_all}</option>
              {ov.regions.map((r) => <option key={r.location} value={r.location}>{r.location}</option>)}
            </select>
          </label>
          <label htmlFor="f-pvp">{t.pvp}
            <select id="f-pvp" name="pvp" defaultValue={pvp}>
              <option value="">{t.filter_all}</option>
              {pvps.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </label>
          <input type="hidden" name="sort" value={sort} />
          <button type="submit">{t.filter_apply}</button>
        </form>
        {showH && (
          <p className="seg">
            <span className="muted">{x.sort_by}</span>
            {["online", "health", "trend"].map((k) => <a key={k} href={qs({ sort: k })} aria-current={k === sort ? "true" : undefined}>{x[`sort_${k}`]}</a>)}
          </p>
        )}
        {hl && !hl.ready && <p className="muted">{fmt(x.home_health_wait, { n: hl.days_needed, d: Math.max(1, Math.ceil(hl.days_needed - hl.days_collected)) })}</p>}
        <div className="tbl">
          <table>
            <thead><tr>
              <th>{t.world}</th><th className="n">{t.online_now}</th>
              {showH && <><th className="n">{x.health_col}</th><th className="n">{x.trend_col} {hl.window}d</th></>}
            </tr></thead>
            <tbody>
              {worlds.map((w) => {
                const h = health.get(w.name);
                return (
                  <tr key={w.name}>
                    <td className="place"><a href={`/${locale}/world/${enc(w.name)}`}>{w.name}</a><small>{w.location} · {w.pvp_type}</small></td>
                    <td className="n">{fmtNum(w.players_online, locale)}</td>
                    {showH && <>
                      <td className="n">{h?.score == null ? <span className="muted">–</span> : <span className="score" style={{ "--p": `${h.score}%` }}>{h.score}</span>}</td>
                      <td className={`n ${trendClass(h?.trend_pct)}`}>{signed(h?.trend_pct, locale, 1)}</td>
                    </>}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
