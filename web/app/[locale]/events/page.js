import { getFlags, on } from "../../../lib/flags";
import { notFound } from "next/navigation";
import { api, fmtDate, fmtNum } from "../../../lib/api";
import { dict, fmt } from "../../../lib/i18n";
import { it, signed, trendClass } from "../../../lib/insights-i18n";
import { D, seo } from "../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  return seo(locale, "/events", { title: t.events_title, description: t.events_lead });
}

export const dynamic = "force-dynamic";

function group(rows) {
  const out = new Map();
  for (const r of rows) {
    if (!out.has(r.day)) out.set(r.day, []);
    out.get(r.day).push(r);
  }
  return [...out.entries()];
}

function Days({ rows, locale, t }) {
  if (!rows.length) return <p className="muted">–</p>;
  return (
    <div className="tbl"><table>
      <thead><tr><th>{t.day}</th><th>{t.events_title}</th></tr></thead>
      <tbody>
        {group(rows).map(([day, evs]) => (
          <tr key={day}>
            <td>{fmtDate(day, locale)}</td>
            <td className="wrap-cell">{evs.map((e) => <span key={e.name} className={`pill ${e.kind === "calendar" ? "" : "red"}`} style={{ margin: "2px 6px 2px 0" }}>{e.name}</span>)}</td>
          </tr>
        ))}
      </tbody>
    </table></div>
  );
}

export default async function Events({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  const f = await getFlags();
  if (!on(f, "page_events")) notFound();
  const x = it(locale);
  const [d, imp] = await Promise.all([
    api("/v1/events?past=30&ahead=30"),
    on(f, "page_event_impact") ? api("/v1/events/impact") : null,
  ]);
  const span = (a, b) => (a === b ? fmtDate(a, locale) : `${fmtDate(a, locale)} – ${fmtDate(b, locale)}`);
  const upcoming = d.events.filter((e) => e.day > d.today);
  const past = d.events.filter((e) => e.day < d.today).reverse();
  return (
    <>
      <section className="card">
        <h1>{t.events_title}</h1>
        <p className="lead">{t.events_lead}</p>
        <div className="stats">
          <div className="stat"><b style={{ fontSize: 20 }}>{d.boosted?.creature || "–"}</b><span>{t.boosted_creature}</span></div>
          <div className="stat"><b style={{ fontSize: 20 }}>{d.boosted?.boss || "–"}</b><span>{t.boosted_boss}</span></div>
          <div className="stat">
            <b style={{ fontSize: 20 }}>{d.active.length ? d.active.map((e) => e.name).join(", ") : "–"}</b>
            <span>{t.active_events} · {fmtDate(d.today, locale)}</span>
          </div>
        </div>
      </section>
      <div className="grid2">
        <section className="card"><h2>{t.upcoming}</h2><Days rows={upcoming} locale={locale} t={t} /></section>
        <section className="card"><h2>{t.past}</h2><Days rows={past} locale={locale} t={t} /></section>
      </div>
      {imp && (
        <section className="card">
          <h2>{x.impact}</h2>
          <p className="lead">{fmt(x.impact_lead, { w: imp.baseline_weeks })}</p>
          {imp.events.length === 0 ? <p className="muted">{x.impact_none}</p> : (
            <div className="tbl"><table className="compact cards">
              <thead><tr><th>{x.event}</th><th className="n">{x.i_online}</th><th className="n">{x.i_kills}</th><th className="n">{x.i_deaths}</th></tr></thead>
              <tbody>
                {imp.events.map((e) => (
                  <tr key={e.name + e.from}>
                    <td className="place">{e.name}<small>{span(e.from, e.to)}</small></td>
                    {e.status === "ok" ? <>
                      <td className={`n ${trendClass(e.online_pct)}`}>{signed(e.online_pct, locale, 1)}</td>
                      <td className={`n ${trendClass(e.kills_pct)}`}>{signed(e.kills_pct, locale, 1)}</td>
                      <td className={`n ${trendClass(-e.deaths_pct)}`}>{signed(e.deaths_pct, locale, 1)}</td>
                    </> : <td colSpan={3} className="muted">{e.status === "upcoming" ? x.upcoming_event : x.no_baseline}</td>}
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </section>
      )}

      {imp && (
        <section className="card">
          <h2>{x.boosted}</h2>
          <p className="lead">{x.boosted_lead} {imp.boosted_median != null && <b>{fmt(x.boosted_median, { x: imp.boosted_median })}</b>}</p>
          {imp.boosted.length === 0 ? <p className="muted">{x.boosted_wait}</p> : (
            <div className="tbl"><table>
              <thead><tr><th>{x.day}</th><th>{x.creature}</th><th className="n">{x.kills}</th><th className="n">{x.normal}</th><th className="n">{x.times}</th></tr></thead>
              <tbody>
                {imp.boosted.map((b) => (
                  <tr key={b.day}>
                    <td>{fmtDate(b.day, locale)}</td><td>{b.creature}</td><td className="n">{fmtNum(b.kills, locale)}</td>
                    <td className="n">{b.normal == null ? <span className="muted">–</span> : fmtNum(b.normal, locale)}</td>
                    <td className="n">{b.multiplier == null ? <span className="muted">–</span> : <b>{b.multiplier}×</b>}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
          {imp.boosted.some((b) => b.multiplier == null) && <p className="muted" style={{ marginTop: 8 }}>{x.boosted_wait}</p>}
        </section>
      )}

      <p className="muted">tibia.com (via TibiaData) · <a href="https://tibiamarket.top">TibiaMarket</a></p>
    </>
  );
}
