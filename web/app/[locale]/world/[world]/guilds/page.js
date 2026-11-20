import { notFound } from "next/navigation";
import { api, enc, fmtDate, fmtNum } from "../../../../../lib/api";
import { getFlags, on } from "../../../../../lib/flags";
import { dict, fmt } from "../../../../../lib/i18n";
import { it, signed, trendClass } from "../../../../../lib/insights-i18n";
import { seo } from "../../../../../lib/seo";

const DESC = {
  pt: (w) => `Guilds de ${w}: membros, quantos estão ativos, entradas e saídas e trocas entre guilds.`,
  en: (w) => `${w} guilds: members, how many are active, joins and departures and exchanges between guilds.`,
};

export async function generateMetadata({ params }) {
  const { locale, world } = await params;
  const w = decodeURIComponent(world);
  return seo(locale, `/world/${encodeURIComponent(w)}/guilds`, { title: `Guilds · ${w}`, description: DESC[locale === "en" ? "en" : "pt"](w) });
}

export const dynamic = "force-dynamic";

const SORTS = ["members", "active", "net", "level"];

export default async function Guilds({ params, searchParams }) {
  const { locale, world } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const x = it(locale);
  const sort = SORTS.includes(sp.sort) ? sp.sort : "members";
  const [d, f] = await Promise.all([api(`/v1/worlds/${enc(decodeURIComponent(world))}/guilds?sort=${sort}`), getFlags()]);
  if (!d) notFound();
  const base = `/${locale}/world/${enc(d.world)}`;
  const label = { members: x.g_members, active: x.g_active, net: x.g_net, level: x.g_level };
  const young = d.activity_since && (Date.now() - new Date(`${d.activity_since}T12:00:00Z`).getTime()) / 864e5 < d.window;
  return (
    <>
      <section className="card">
        <h2>{x.guilds_title}</h2>
        <p className="lead">{fmt(x.guilds_lead, { a: d.active_days, w: d.window })}</p>
        <div className="stats">
          <div className="stat"><b>{fmtNum(d.guilds, locale)}</b><span>{x.g_guilds}</span></div>
          <div className="stat"><b>{fmtNum(d.joins, locale)}</b><span>{fmt(x.g_joins, { w: d.window })}</span></div>
          <div className="stat"><b>{fmtNum(d.leaves, locale)}</b><span>{fmt(x.g_leaves, { w: d.window })}</span></div>
        </div>
        {young && <p className="muted" style={{ marginTop: 10 }}>{fmt(x.guilds_since, { d: fmtDate(d.activity_since, locale) })}</p>}
      </section>

      <section className="card">
        <p className="seg">
          <span className="muted">{x.sort_by}</span>
          {SORTS.map((s) => <a key={s} href={`${base}/guilds?sort=${s}`} aria-current={s === sort ? "true" : undefined}>{label[s]}</a>)}
        </p>
        {d.rows.length === 0 ? <p className="muted">{t.not_yet}</p> : (
          <div className="tbl"><table>
            <thead><tr>
              <th>#</th><th>{t.guilds}</th><th className="n">{x.g_members}</th><th className="n">{fmt(x.g_active_col, { a: d.active_days })}</th>
              <th className="n">{fmt(x.g_moves_col, { w: d.window })}</th><th className="n">{x.g_level}</th><th>{x.g_war}</th>
            </tr></thead>
            <tbody>
              {d.rows.map((g, i) => (
                <tr key={g.name}>
                  <td>{i + 1}</td>
                  <td><a href={`${base}/guild/${enc(g.name)}`}>{g.name}</a></td>
                  <td className="n">{fmtNum(g.members_total, locale)}</td>
                  <td className="n">{g.active_pct == null ? "–" : <span className="meter" style={{ "--p": `${g.active_pct}%` }}>{g.active_pct}%</span>}</td>
                  <td className="n"><span className="up">{fmtNum(g.joins, locale)}</span> / <span className={g.leaves ? "down" : undefined}>{fmtNum(g.leaves, locale)}</span></td>
                  <td className="n">{fmtNum(g.avg_level, locale)}</td>
                  <td>{g.in_war == null ? "–" : g.in_war ? <span className="pill red">{t.yes}</span> : t.no}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </section>

      {on(f, "page_guild_exchange") && (
        <section className="card">
          <h2>{x.exchange}</h2>
          <p className="lead">{fmt(x.exchange_lead, { n: d.min_cell, g: d.gap_days, w: d.window })}</p>
          {d.exchanges.length === 0 ? <p className="muted">{x.exchange_none}</p> : (
            <div className="tbl"><table>
              <thead><tr><th>{x.from_guild}</th><th>{x.to_guild}</th><th className="n">{x.people}</th></tr></thead>
              <tbody>
                {d.exchanges.map((e) => (
                  <tr key={e.from_guild + e.to_guild}>
                    <td><a href={`${base}/guild/${enc(e.from_guild)}`}>{e.from_guild}</a></td>
                    <td><a href={`${base}/guild/${enc(e.to_guild)}`}>{e.to_guild}</a></td>
                    <td className="n">{fmtNum(e.n, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </section>
      )}
    </>
  );
}
