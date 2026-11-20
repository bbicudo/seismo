import { notFound } from "next/navigation";
import { Bars, DayBars, Heatmap } from "../../../../../components/charts";
import { api, enc, fmtDate, fmtNum } from "../../../../../lib/api";
import { getFlags, on } from "../../../../../lib/flags";
import { BANDS, TZ, TZ_LABEL, VOCATIONS, VOC_LABEL, dict, fmt } from "../../../../../lib/i18n";
import { it, signed, trendClass } from "../../../../../lib/insights-i18n";
import { seo } from "../../../../../lib/seo";

const DESC = {
  pt: (w) => `Quando ${w} joga, vocações em alta, velocidade de up e quantos novatos ficam.`,
  en: (w) => `When ${w} plays, trending vocations, leveling speed and how many newcomers stay.`,
};

export async function generateMetadata({ params }) {
  const { locale, world } = await params;
  const w = decodeURIComponent(world);
  const x = it(locale);
  return seo(locale, `/world/${encodeURIComponent(w)}/activity`, { title: `${x.tab_activity} · ${w}`, description: DESC[locale === "en" ? "en" : "pt"](w) });
}

export const dynamic = "force-dynamic";

// Tempo médio para subir um level, sempre na mesma unidade (relógio), para dar para comparar as células.
function Speed({ c, x }) {
  if (!c || c.levels_per_hour == null) return <span className="muted">–</span>;
  const v = c.levels_per_hour;
  if (v <= 0) return <span className="muted">–</span>;
  const min = Math.round(60 / v);
  const text = min < 60 ? fmt(x.t_min, { m: min }) : min % 60 === 0 || min >= 600
    ? fmt(x.t_h, { h: Math.round(min / 60) }) : fmt(x.t_hmin, { h: Math.floor(min / 60), m: String(min % 60).padStart(2, "0") });
  return <span title={fmt(x.lvl_players, { n: c.players })}>{text}</span>;
}

export default async function Activity({ params, searchParams }) {
  const { locale, world } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const x = it(locale);
  const name = decodeURIComponent(world);
  const f = await getFlags();
  const vocation = VOCATIONS.includes(sp.vocation) ? sp.vocation : "";
  const band = BANDS.includes(sp.band) ? sp.band : "";
  const evmode = ["exclude", "only", "include"].includes(sp.events) ? sp.events : "exclude";
  const hq = new URLSearchParams({ tz: TZ[locale], events: evmode });
  if (vocation) hq.set("vocation", vocation);
  if (band) hq.set("band", band);
  const w = `/v1/worlds/${enc(name)}`;
  const [heat, voc, lvl, nc] = await Promise.all([
    on(f, "page_heatmap") ? api(`${w}/heatmap?${hq}`) : null,
    on(f, "page_vocations") ? api(`${w}/vocations`) : null,
    on(f, "page_leveling") ? api(`${w}/leveling`) : null,
    on(f, "page_funnel") || on(f, "page_retention") ? api(`${w}/newcomers`) : null,
  ]);
  if (!heat && !voc && !lvl && !nc) notFound();
  const base = `/${locale}/world/${enc(name)}/activity`;
  const heatHasData = !!heat && heat.cells.some((c) => c.avg != null);
  const today = new Date().toISOString().slice(0, 10);
  const from30 = new Date(Date.now() - 29 * 864e5).toISOString().slice(0, 10);
  const firstDay = nc?.daily?.[0]?.day;
  const nf1 = (n) => (n == null ? "–" : new Intl.NumberFormat(locale === "en" ? "en-GB" : "pt-BR", { maximumFractionDigits: 1 }).format(n));
  return (
    <>
      {heat && (
        <section className="card" id="heatmap">
          <h2>{t.heatmap}</h2>
          <p className="lead">{fmt(t.heatmap_lead, { tz: TZ_LABEL[locale] })}</p>
          <form className="filters" method="get" action={`${base}#heatmap`}>
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

      {voc && (
        <section className="card">
          <h2>{x.vocations}</h2>
          <p className="lead">{fmt(x.vocations_lead, { w: voc.window, n: voc.min_cell })} {voc.compare ? fmt(x.vocations_cmp, { w: voc.window }) : x.vocations_nocmp}</p>
          <div className="tbl"><table>
            <thead><tr>
              <th>{t.vocation}</th>
              {voc.bands.map((b) => <th key={b} className="n">{b}</th>)}
              <th className="n">{x.avg_online}</th><th className="n">{x.share}</th>{voc.compare && <th className="n">{x.delta}</th>}
            </tr></thead>
            <tbody>
              {voc.vocations.filter((v) => v.avg_online != null).map((v) => (
                <tr key={v.vocation}>
                  <td>{VOC_LABEL[locale][v.vocation] || v.vocation}</td>
                  {voc.bands.map((b) => <td key={b} className="n">{v.bands[b] == null ? <span className="muted">&lt;{voc.min_cell}</span> : nf1(v.bands[b])}</td>)}
                  <td className="n"><b>{nf1(v.avg_online)}</b></td>
                  <td className="n">{v.share == null ? "–" : `${nf1(v.share)}%`}</td>
                  {voc.compare && <td className={`n ${trendClass(v.delta_pp)}`}>{signed(v.delta_pp, locale, 1, ` ${x.pp}`)}</td>}
                </tr>
              ))}
            </tbody>
          </table></div>
        </section>
      )}

      {lvl && (
        <section className="card">
          <h2>{x.leveling}</h2>
          <p className="lead">{fmt(x.leveling_lead, { d: fmtDate(lvl.since, locale), h: lvl.min_hours })} </p>
          {lvl.vocations.length === 0 ? <p className="muted">{t.not_yet}</p> : (
            <div className="tbl"><table>
              <thead><tr><th>{t.vocation}</th>{lvl.bands.map((b) => <th key={b} className="n">{b}</th>)}</tr></thead>
              <tbody>
                {lvl.vocations.filter((v) => v.vocation !== "none").map((v) => (
                  <tr key={v.vocation}>
                    <td>{VOC_LABEL[locale][v.vocation] || v.vocation}</td>
                    {lvl.bands.map((b) => <td key={b} className="n"><Speed c={v.bands[b]} x={x} /></td>)}
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </section>
      )}

      {nc && (
        <div className="grid-even">
          {on(f, "page_funnel") && (
            <section className="card">
              <h2>{x.newcomers}</h2>
              <p className="lead">{fmt(x.newcomers_lead, { n: nc.new_level_max })}</p>
              {nc.daily.length === 0 ? <p className="muted">{t.new_chars_wait}</p> : (
                <>
                  <DayBars points={nc.daily.map((d) => ({ day: d.day, v: d.n }))} from={firstDay && firstDay > from30 ? firstDay : from30}
                           to={today} locale={locale} label={x.daily_new} unit="" height={130} />
                  <Bars rows={[
                    { label: fmt(x.created_total, { w: nc.weeks }), v: nc.created },
                    ...nc.funnel.map((s) => ({ label: fmt(x.reached, { l: s.level }), v: s.n, note: nc.created ? `${Math.round((100 * s.n) / nc.created)}%` : "" })),
                  ]} locale={locale} />
                </>
              )}
            </section>
          )}
          {on(f, "page_retention") && (
            <section className="card">
              <h2>{x.retention}</h2>
              <p className="lead">{fmt(x.retention_lead, { m: nc.marks.join("/"), n: nc.min_cell })}</p>
              {nc.cohorts.length === 0 ? <p className="muted">{t.new_chars_wait}</p> : (
                <div className="tbl"><table>
                  <thead><tr><th>{x.week}</th><th className="n">{x.created}</th>{nc.marks.map((mk) => <th key={mk} className="n">{fmt(x.after_days, { d: mk })}</th>)}</tr></thead>
                  <tbody>
                    {nc.cohorts.map((c) => (
                      <tr key={c.week}>
                        <td>{fmtDate(c.week, locale)}</td>
                        <td className="n">{fmtNum(c.created, locale)}</td>
                        {c.retention.map((r, i) => <td key={i} className="n">{r == null ? <span className="muted">–</span> : `${r}%`}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              )}
            </section>
          )}
        </div>
      )}
    </>
  );
}
