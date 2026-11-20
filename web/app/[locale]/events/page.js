import { getFlags, on } from "../../../lib/flags";
import { notFound } from "next/navigation";
import { api, fmtDate } from "../../../lib/api";
import { dict } from "../../../lib/i18n";

export const dynamic = "force-dynamic";
export const metadata = { title: "Eventos · Events" };

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
      <thead><tr><th>{t.day}</th><th>{t.events_title}</th><th>{t.event_source}</th></tr></thead>
      <tbody>
        {group(rows).map(([day, evs]) => (
          <tr key={day}>
            <td>{fmtDate(day, locale)}</td>
            <td>{evs.map((e) => <span key={e.name} className={`pill ${e.kind === "calendar" ? "" : "red"}`} style={{ marginRight: 6 }}>{e.name}</span>)}</td>
            <td className="muted">{[...new Set(evs.map((e) => e.source))].join(", ")}</td>
          </tr>
        ))}
      </tbody>
    </table></div>
  );
}

export default async function Events({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  if (!on(await getFlags(), "page_events")) notFound();
  const d = await api("/v1/events?past=30&ahead=30");
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
      <p className="muted">tibia.com (via TibiaData) · <a href="https://tibiamarket.top">TibiaMarket</a></p>
    </>
  );
}
