import { notFound } from "next/navigation";
import { Heatmap, TimeChart } from "../../../../components/charts";
import { api, enc, fmtDate, fmtNum, fmtTime } from "../../../../lib/api";
import { getFlags, on } from "../../../../lib/flags";
import { BANDS, TZ, TZ_LABEL, VOCATIONS, VOC_LABEL, dict, fmt } from "../../../../lib/i18n";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { world } = await params;
  return { title: decodeURIComponent(world) };
}

export default async function World({ params, searchParams }) {
  const { locale, world } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const name = decodeURIComponent(world);
  const vocation = VOCATIONS.includes(sp.vocation) ? sp.vocation : "";
  const band = BANDS.includes(sp.band) ? sp.band : "";
  const days = [7, 14, 30].includes(Number(sp.days)) ? Number(sp.days) : 14;
  const evmode = ["exclude", "only", "include"].includes(sp.events) ? sp.events : "exclude";
  const hq = new URLSearchParams({ tz: TZ[locale], events: evmode });
  if (vocation) hq.set("vocation", vocation);
  if (band) hq.set("band", band);
  const [w, health, heat, f] = await Promise.all([
    api(`/v1/worlds/${enc(name)}`),
    api(`/v1/worlds/${enc(name)}/health?days=${days}`),
    api(`/v1/worlds/${enc(name)}/heatmap?${hq}`),
    getFlags(),
  ]);
  if (!w) notFound();
  const points = health.hourly.map((h) => ({ t: h.hour, v: h.avg, peak: h.max }));
  const heatHasData = !!heat && heat.cells.some((c) => c.avg != null);
  const base = `/${locale}/world/${enc(w.name)}`;
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={`/${locale}`}>← {t.back_worlds}</a></p>
        <h1>{w.name}</h1>
        <p className="lead">{w.location} · {w.pvp_type} · {fmtTime(w.updated_at, locale)}{on(f, "page_raids") && <> · <a href={`/${locale}/world/${enc(w.name)}/raids`}>Raids →</a></>}{on(f, "page_wrapped") && <> · <a href={`/${locale}/wrapped/${enc(w.name)}`}>Wrapped →</a></>}</p>
        <div className="stats">
          <div className="stat"><b>{fmtNum(w.players_online, locale)}</b><span>{t.online_now}</span></div>
          <div className="stat"><b>{fmtNum(health.record?.players_online, locale)}</b><span>{t.record}</span></div>
          <div className="stat"><b>{fmtNum(health.transfers.arrived, locale)}</b><span>{t.transfers_in} ({days}d)</span></div>
          <div className="stat"><b>{fmtNum(health.transfers.left, locale)}</b><span>{t.transfers_out} ({days}d)</span></div>
          <div className="stat"><b>{fmtNum(health.new_characters, locale)}</b><span>{t.new_characters} ({days}d)</span></div>
          <div className="stat"><b>{fmtNum(health.deaths_by_day.at(-1)?.deaths, locale)}</b><span>{t.deaths} ({health.deaths_by_day.length ? fmtDate(health.deaths_by_day.at(-1).stats_day, locale) : "–"})</span></div>
        </div>
        <p className="muted">{fmt(t.collecting_since, { date: fmtDate(health.collecting_since, locale) })}</p>
      </section>

      {on(f, "page_health") && (
      <section className="card">
        <h2>{t.health}</h2>
        <p className="lead">
          {fmt(t.health_lead, { days })}{" "}
          {[7, 14, 30].map((d) => (
            <a key={d} href={`${base}?days=${d}`} style={{ marginRight: 8, fontWeight: d === days ? 700 : 400 }}>{d}d</a>
          ))}
        </p>
        <TimeChart points={points} locale={locale} label={fmt(t.health_lead, { days })} peakLabel={t.peak} shade={health.event_days} />
        <div className="legend"><span><i />{t.avg}</span><span><i className="dash" />{t.peak}</span>{health.event_days.length > 0 && <span><i className="box" />{t.event_days_legend}</span>}</div>
      </section>
      )}

      {on(f, "page_new_characters") && (
      <section className="card" id="new-characters">
        <h2>{t.created_title}</h2>
        <p className="lead">{fmt(t.new_chars_note, { n: health.new_level_max })}</p>
        {health.new_characters_by_day.length === 0 ? <p className="muted">{t.new_chars_wait}</p> : (
          <div className="tbl">
            <table>
              <thead><tr><th>{t.day}</th><th className="n">{t.new_characters}</th><th className="n">{t.without_vocation}</th></tr></thead>
              <tbody>
                {health.new_characters_by_day.map((r) => (
                  <tr key={r.day}>
                    <td>{fmtDate(r.day, locale)}</td>
                    <td className="n">{fmtNum(r.new_characters, locale)}</td>
                    <td className="n">{fmtNum(r.without_vocation, locale)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr><th>{t.total} ({days}d)</th><th className="n">{fmtNum(health.new_characters, locale)}</th><th /></tr>
              </tfoot>
            </table>
          </div>
        )}
      </section>
      )}

      {on(f, "page_heatmap") && (
      <section className="card" id="heatmap">
        <h2>{t.heatmap}</h2>
        <p className="lead">{fmt(t.heatmap_lead, { tz: TZ_LABEL[locale] })}</p>
        <form className="filters" method="get" action={`${base}#heatmap`}>
          <input type="hidden" name="days" value={days} />
          <label htmlFor="f-voc">{t.vocation}
            <select id="f-voc" name="vocation" defaultValue={vocation}>
              <option value="">{t.filter_all}</option>
              {VOCATIONS.map((v) => <option key={v} value={v}>{VOC_LABEL[locale][v]}</option>)}
            </select>
          </label>
          <label htmlFor="f-band">{t.band}
            <select id="f-band" name="band" defaultValue={band}>
              <option value="">{t.filter_all}</option>
              {BANDS.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>
          <label htmlFor="f-ev">{t.heat_events}
            <select id="f-ev" name="events" defaultValue={evmode}>
              <option value="exclude">{t.heat_exclude}</option>
              <option value="only">{t.heat_only}</option>
              <option value="include">{t.heat_include}</option>
            </select>
          </label>
          <button type="submit">{t.filter_apply}</button>
        </form>
        {heatHasData ? <Heatmap cells={heat.cells} weekdays={t.weekdays} locale={locale} /> : <p className="muted">{t.heatmap_empty}</p>}
        {(vocation || band) && <p className="muted">{fmt(t.heatmap_hidden, { n: heat.min_cell })}</p>}
      </section>
      )}

      <div className="grid2">
        {on(f, "page_kills") && (
        <section className="card">
          <h2>{t.kills}</h2>
          {w.kills_last_day.length === 0 ? <p className="muted">{t.not_yet}</p> : (
            <>
              <p className="lead">{fmt(t.kills_lead, { date: fmtDate(w.kills_last_day[0].stats_day, locale) })}</p>
              <div className="tbl">
                <table>
                  <thead><tr><th>{t.creature}</th><th className="n">{t.killed}</th><th className="n">{t.players_killed}</th></tr></thead>
                  <tbody>
                    {w.kills_last_day.map((k) => (
                      <tr key={k.race}><td>{k.race}</td><td className="n">{fmtNum(k.killed, locale)}</td><td className="n">{fmtNum(k.players_killed, locale)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
        )}
        {on(f, "page_composition") && (
        <section className="card">
          <h2>{t.composition}</h2>
          <p className="lead">{fmt(t.composition_lead, { n: w.min_cell })}</p>
          <div className="tbl">
            <table>
              <thead><tr><th>{t.vocation}</th><th>{t.band}</th><th className="n">{t.players}</th></tr></thead>
              <tbody>
                {w.composition.map((r) => (
                  <tr key={r.vocation + r.level_band}>
                    <td>{r.vocation}</td><td>{r.level_band}</td>
                    <td className="n">{r.players == null ? `<${w.min_cell}` : fmtNum(r.players, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        )}
      </div>

      <div className="grid2">
        {on(f, "page_guilds") && (
        <section className="card">
          <h2>{t.guilds}</h2>
          <p className="lead">{fmt(t.guild_moves, { joins: fmtNum(w.guild_moves_7d.joins, locale), leaves: fmtNum(w.guild_moves_7d.leaves, locale) })}</p>
          {w.guilds.length === 0 ? <p className="muted">{t.not_yet}</p> : (
            <div className="tbl">
              <table>
                <thead><tr><th>{t.guilds}</th><th className="n">{t.members}</th><th>{t.founded}</th><th>{t.in_war}</th></tr></thead>
                <tbody>
                  {w.guilds.map((g) => (
                    <tr key={g.name}>
                      <td><a href={`${base}/guild/${enc(g.name)}`}>{g.name}</a></td>
                      <td className="n">{fmtNum(g.members_total, locale)}</td>
                      <td>{g.founded ? fmtDate(g.founded, locale) : "–"}</td>
                      <td>{g.in_war == null ? "–" : g.in_war ? t.yes : t.no}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        )}
        {on(f, "page_houses") && (
        <section className="card">
          <h2>{t.houses_by_town}</h2>
          {w.houses_by_town.length === 0 ? <p className="muted">{t.not_yet}</p> : (
            <div className="tbl">
              <table>
                <thead><tr><th>{t.town}</th><th className="n">{t.total}</th><th className="n">{t.rented}</th><th className="n">{t.auctioned}</th></tr></thead>
                <tbody>
                  {w.houses_by_town.map((h) => (
                    <tr key={h.town}>
                      <td><a href={`${base}/town/${enc(h.town)}`}>{h.town}</a></td>
                      <td className="n">{fmtNum(h.total, locale)}</td><td className="n">{fmtNum(h.rented, locale)}</td><td className="n">{fmtNum(h.auctioned, locale)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        )}
      </div>
    </>
  );
}
