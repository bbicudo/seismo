import { notFound } from "next/navigation";
import { api, enc, fmtDate, fmtNum } from "../../../../../../lib/api";
import { TZ, TZ_LABEL, VOC_LABEL, dict, fmt } from "../../../../../../lib/i18n";
import { Heatmap } from "../../../../../../components/charts";
import { getFlags, on } from "../../../../../../lib/flags";
import { D, seo } from "../../../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale, world, guild } = await params;
  const w = decodeURIComponent(world), g = decodeURIComponent(guild);
  return seo(locale, `/world/${encodeURIComponent(w)}/guild/${encodeURIComponent(g)}`, { title: `${g} · ${w}`, description: D.guild[locale === "en" ? "en" : "pt"](g, w) });
}

const HT = {
  pt: { title: "Quando a guild joga", lead: "Média de membros online por dia da semana e hora ({tz}). Só a contagem: ninguém é identificado.",
        small: "Mapa de calor só para guilds com pelo menos {n} membros, para proteger grupos pequenos.",
        hidden: "Células com média abaixo de {n} membros ficam vazias.", empty: "Ainda não há horas suficientes. O mapa se completa em uma semana de coleta.",
        events: "Dias de evento", exclude: "sem eventos", only: "só eventos", include: "todos os dias", apply: "Filtrar" },
  en: { title: "When the guild plays", lead: "Average members online by weekday and hour ({tz}). Counts only: nobody is identified.",
        small: "Heatmaps are only shown for guilds with at least {n} members, to protect small groups.",
        hidden: "Cells averaging under {n} members stay empty.", empty: "Not enough hours yet. The map fills in after one week of collection.",
        events: "Event days", exclude: "without events", only: "events only", include: "all days", apply: "Filter" },
};

export const dynamic = "force-dynamic";


export default async function Guild({ params, searchParams }) {
  const { locale, world, guild } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const ht = HT[locale] || HT.pt;
  const evmode = ["exclude", "only", "include"].includes(sp.events) ? sp.events : "exclude";
  const g = await api(`/v1/worlds/${enc(decodeURIComponent(world))}/guilds/${enc(decodeURIComponent(guild))}`);
  if (!g) notFound();
  const [heat, f] = await Promise.all([
    api(`/v1/worlds/${enc(g.world)}/guilds/${enc(g.name)}/heatmap?tz=${TZ[locale]}&events=${evmode}`),
    getFlags(),
  ]);
  const heatHasData = !!heat && heat.eligible && heat.cells.some((c) => c.avg != null);
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

      {heat && on(f, "page_heatmap") && (
        <section className="card" id="heatmap">
          <h2>{ht.title}</h2>
          {!heat.eligible ? <p className="muted">{fmt(ht.small, { n: heat.min_members })}</p> : (
            <>
              <p className="lead">{fmt(ht.lead, { tz: TZ_LABEL[locale] })}</p>
              <form className="filters" method="get" action="#heatmap">
                <label htmlFor="g-ev">{ht.events}
                  <select id="g-ev" name="events" defaultValue={evmode}>
                    <option value="exclude">{ht.exclude}</option>
                    <option value="only">{ht.only}</option>
                    <option value="include">{ht.include}</option>
                  </select>
                </label>
                <button type="submit">{ht.apply}</button>
              </form>
              {heatHasData ? <Heatmap cells={heat.cells} weekdays={t.weekdays} locale={locale} /> : <p className="muted">{ht.empty}</p>}
              <p className="muted">{fmt(ht.hidden, { n: heat.min_cell })}</p>
            </>
          )}
        </section>
      )}

      <div className="grid2">
        <section className="card">
          <h2>{t.members}</h2>
          <div className="tbl">
            <table>
              <thead><tr><th>{t.name}</th><th>{t.rank}</th><th>{t.vocation}</th><th className="n">{t.level}</th><th>{t.joined}</th></tr></thead>
              <tbody>
                {g.members.map((m) => (
                  <tr key={m.name}>
                    <td><a href={`/${locale}/character/${enc(m.name)}`}>{m.name}</a></td><td>{m.rank}</td><td>{m.vocation}</td>
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
