import { notFound } from "next/navigation";
import { api, enc, fmtDate, fmtNum } from "../../../../../../lib/api";
import { VOC_LABEL, dict } from "../../../../../../lib/i18n";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { guild } = await params;
  return { title: decodeURIComponent(guild) };
}

export default async function Guild({ params }) {
  const { locale, world, guild } = await params;
  const t = dict(locale);
  const g = await api(`/v1/worlds/${enc(decodeURIComponent(world))}/guilds/${enc(decodeURIComponent(guild))}`);
  if (!g) notFound();
  const base = `/${locale}/world/${enc(g.world)}`;
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={`/${locale}`}>{t.nav_worlds}</a> / <a href={base}>{g.world}</a></p>
        <h1>{g.name}</h1>
        <p className="lead">{t.guild_lead} <a href={`/${locale}/wrapped/${enc(g.world)}/guild/${enc(g.name)}`}>Wrapped →</a></p>
        {!g.details_fetched_at ? <p className="muted">{t.guild_not_read}</p> : (
          <div className="stats">
            <div className="stat"><b>{fmtNum(g.members_total, locale)}</b><span>{t.members}</span></div>
            <div className="stat"><b>{g.founded ? fmtDate(g.founded, locale) : "–"}</b><span>{t.founded}</span></div>
            <div className="stat"><b>{g.in_war ? t.yes : t.no}</b><span>{t.in_war}</span></div>
            <div className="stat"><b>{g.open_applications ? t.yes : t.no}</b><span>{t.applications}</span></div>
          </div>
        )}
        {Object.keys(g.vocations).length > 0 && (
          <div className="voc" style={{ marginTop: 12 }} aria-label={t.vocations_mix}>
            {Object.entries(g.vocations).sort((a, b) => b[1] - a[1]).map(([v, n]) => (
              <span key={v}>{VOC_LABEL[locale][v] || v}: {fmtNum(n, locale)}</span>
            ))}
          </div>
        )}
      </section>

      <div className="grid2">
        <section className="card">
          <h2>{t.members}</h2>
          <div className="tbl">
            <table>
              <thead><tr><th>{t.name}</th><th>{t.rank}</th><th>{t.vocation}</th><th className="n">{t.level}</th><th>{t.joined}</th></tr></thead>
              <tbody>
                {g.members.map((m) => (
                  <tr key={m.name}>
                    <td>{m.name}</td><td>{m.rank}</td><td>{m.vocation}</td>
                    <td className="n">{fmtNum(m.level, locale)}</td><td>{m.joined ? fmtDate(m.joined, locale) : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="card">
          <h2>{t.events}</h2>
          {g.events.length === 0 ? <p className="muted">{t.no_events}</p> : (
            <div className="tbl">
              <table>
                <thead><tr><th>{t.day}</th><th>{t.name}</th><th /></tr></thead>
                <tbody>
                  {g.events.map((e) => (
                    <tr key={e.name + e.event_day + e.event}>
                      <td>{fmtDate(e.event_day, locale)}</td><td>{e.name}</td>
                      <td><span className={`pill ${e.event === "join" ? "on" : "red"}`}>{e.event === "join" ? t.event_join : t.event_leave}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
