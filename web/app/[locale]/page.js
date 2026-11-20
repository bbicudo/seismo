import { TimeChart } from "../../components/charts";
import { api, enc, fmtDate, fmtNum } from "../../lib/api";
import { dict, fmt } from "../../lib/i18n";
import { getFlags, on } from "../../lib/flags";
import CharacterSearch from "../../components/character-search";

export const dynamic = "force-dynamic";

export default async function Overview({ params, searchParams }) {
  const { locale } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const [ov, all, ev, f] = await Promise.all([api("/v1/overview"), api("/v1/worlds"), api("/v1/events?past=0&ahead=7"), getFlags()]);
  const region = sp.region || "";
  const pvp = sp.pvp || "";
  const worlds = all.filter((w) => (!region || w.location === region) && (!pvp || w.pvp_type === pvp));
  const total = all.reduce((s, w) => s + (w.players_online || 0), 0);
  const pvps = [...new Set(all.map((w) => w.pvp_type))].sort();
  const points = ov.series_48h.map((p) => ({ t: p.ts, v: p.players_online }));
  const peak48 = points.length ? Math.max(...points.map((p) => p.v)) : null;
  return (
    <>
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

      <div className="grid2">
        <section className="card">
          <h2>{t.total_48h}</h2>
          <TimeChart points={points} locale={locale} label={t.total_48h} peakLabel={t.peak} />
        </section>
        <section className="card">
          <h2>{t.by_region}</h2>
          <div className="tbl">
            <table>
              <thead><tr><th>{t.region}</th><th className="n">{t.worlds}</th><th className="n">{t.online_now}</th></tr></thead>
              <tbody>
                {ov.regions.map((r) => (
                  <tr key={r.location}>
                    <td><a href={`/${locale}?region=${enc(r.location)}`}>{r.location}</a></td>
                    <td className="n">{fmtNum(r.worlds, locale)}</td><td className="n">{fmtNum(r.players_online, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {on(f, "page_kills") && <div>
        <section className="card">
          <h2>{t.top_deaths}</h2>
          {ov.top_deaths.length === 0 ? <p className="muted">{t.not_yet}</p> : (
            <>
              <p className="lead">{fmt(t.top_deaths_lead, { date: fmtDate(ov.top_deaths[0].stats_day, locale) })}</p>
              <div className="tbl">
                <table>
                  <thead><tr><th>#</th><th>{t.world}</th><th className="n">{t.deaths}</th><th className="n">{t.creatures_killed}</th></tr></thead>
                  <tbody>
                    {ov.top_deaths.map((d, i) => (
                      <tr key={d.name}>
                        <td>{i + 1}</td>
                        <td><a href={`/${locale}/world/${enc(d.name)}`}>{d.name}</a></td>
                        <td className="n">{fmtNum(d.deaths, locale)}</td>
                        <td className="n">{fmtNum(d.creatures_killed, locale)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </div>}

      <section className="card">
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
          <button type="submit">{t.filter_apply}</button>
        </form>
        <div className="tbl">
          <table>
            <thead><tr><th>{t.world}</th><th className="n">{t.online_now}</th><th>{t.location}</th><th>{t.pvp}</th><th>{t.battleye}</th></tr></thead>
            <tbody>
              {worlds.map((w) => (
                <tr key={w.name}>
                  <td><a href={`/${locale}/world/${enc(w.name)}`}>{w.name}</a></td>
                  <td className="n">{fmtNum(w.players_online, locale)}</td>
                  <td>{w.location}</td><td>{w.pvp_type}</td><td>{w.battleye_protected ? t.yes : t.no}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
