import { notFound } from "next/navigation";
import { api, enc, fmtDate, fmtNum } from "../../../../../lib/api";
import { dict, fmt } from "../../../../../lib/i18n";
import { D, seo } from "../../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale, world } = await params;
  const w = decodeURIComponent(world);
  return seo(locale, `/world/${encodeURIComponent(w)}/raids`, { title: `Raids · ${w}`, description: D.raids[locale === "en" ? "en" : "pt"](w) });
}

const DICT = { pt: dict("pt"), en: dict("en") };

export const dynamic = "force-dynamic";

const T = {
  pt: {
    title: "Raids e termômetro",
    back: "voltar ao mundo",
    lead: "Raids detectadas pelas kill statistics: quando uma criatura que só aparece em raid é morta, sabemos que a raid aconteceu naquele dia.",
    recent: "Raids recentes",
    none: "Nenhuma raid detectada ainda. O histórico começou há {n} dia(s).",
    raid: "Raid",
    region: "Região",
    day: "Dia",
    kills: "Mortes",
    summary: "Frequência e próxima janela",
    summary_lead: "A janela é uma estimativa a partir dos intervalos entre ocorrências (precisa de pelo menos 3). Não é uma data certa.",
    count: "Vezes",
    last: "Última",
    gap: "Intervalo típico",
    next: "Próxima janela provável",
    days_word: "dias",
    unknown: "poucos dados",
    detectable: "{d} de {t} raids da TibiaWiki têm criaturas raras o bastante para serem detectadas.",
    thermo: "Termômetro de respawn",
    thermo_lead: "Compara as mortes do dia {day} com a média dos 28 dias anteriores neste mundo.",
    thermo_wait: "O termômetro precisa de pelo menos {n} dias de histórico. Hoje temos {h}.",
    hot: "Em alta (spot provavelmente lotado)",
    cold: "Em queda (spot provavelmente livre)",
    creature: "Criatura",
    today: "No dia",
    average: "Média",
    nothing: "Nada fora do normal.",
    credit: "Lista de raids e criaturas: TibiaWiki (tibia.fandom.com), licença CC BY-SA.",
  },
  en: {
    title: "Raids and thermometer",
    back: "back to the world",
    lead: "Raids detected from kill statistics: when a creature that only shows up in a raid is killed, we know the raid happened that day.",
    recent: "Recent raids",
    none: "No raids detected yet. History started {n} day(s) ago.",
    raid: "Raid",
    region: "Region",
    day: "Day",
    kills: "Kills",
    summary: "Frequency and next window",
    summary_lead: "The window is an estimate from the gaps between occurrences (needs at least 3). It is not an exact date.",
    count: "Times",
    last: "Last",
    gap: "Typical gap",
    next: "Likely next window",
    days_word: "days",
    unknown: "not enough data",
    detectable: "{d} of {t} TibiaWiki raids have creatures rare enough to be detected.",
    thermo: "Respawn thermometer",
    thermo_lead: "Compares kills on {day} with the average of the previous 28 days in this world.",
    thermo_wait: "The thermometer needs at least {n} days of history. We have {h} so far.",
    hot: "Running hot (spot likely crowded)",
    cold: "Cooling down (spot likely free)",
    creature: "Creature",
    today: "That day",
    average: "Average",
    nothing: "Nothing out of the ordinary.",
    credit: "Raid and creature list: TibiaWiki (tibia.fandom.com), CC BY-SA license.",
  },
};

function Thermo({ title, rows, t, locale, boostedTag }) {
  return (
    <div>
      <h2 style={{ marginTop: 12 }}>{title}</h2>
      {rows.length === 0 ? <p className="muted">{t.nothing}</p> : (
        <div className="tbl"><table>
          <thead><tr><th>{t.creature}</th><th className="n">{t.today}</th><th className="n">{t.average}</th><th className="n">z</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.race}><td>{r.race}{r.boosted && <span className="pill off" style={{ marginLeft: 6 }}>{boostedTag}</span>}</td><td className="n">{fmtNum(r.killed, locale)}</td>
                <td className="n">{fmtNum(r.average, locale)}</td><td className="n">{r.z > 0 ? "+" : ""}{r.z}</td></tr>
            ))}
          </tbody>
        </table></div>
      )}
    </div>
  );
}


export default async function Raids({ params }) {
  const { locale, world } = await params;
  const t = T[locale] || T.pt;
  const name = decodeURIComponent(world);
  const [r, th] = await Promise.all([api(`/v1/worlds/${enc(name)}/raids`), api(`/v1/worlds/${enc(name)}/thermometer`)]);
  if (!r) notFound();
  const base = `/${locale}/world/${enc(r.world)}`;
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={base}>← {t.back}</a></p>
        <h1>{t.title} · {r.world}</h1>
        <p className="lead">{t.lead}</p>
        <p className="muted">{fmt(t.detectable, { d: r.detectable, t: r.total })}</p>
      </section>

      <div className="grid2">
        <section className="card">
          <h2>{t.recent}</h2>
          {r.recent.length === 0 ? <p className="muted">{fmt(t.none, { n: r.history_days })}</p> : (
            <div className="tbl"><table>
              <thead><tr><th>{t.day}</th><th>{t.raid}</th><th>{t.region}</th><th className="n">{t.kills}</th></tr></thead>
              <tbody>
                {r.recent.map((o) => (
                  <tr key={o.slug + o.day}><td>{fmtDate(o.day, locale)}</td><td>{o.name}</td><td>{o.region}</td><td className="n">{fmtNum(o.kills, locale)}</td></tr>
                ))}
              </tbody>
            </table></div>
          )}
        </section>
        <section className="card">
          <h2>{t.thermo}</h2>
          {r.history_days < th.min_days ? <p className="muted">{fmt(t.thermo_wait, { n: th.min_days, h: th.history_days })}</p> : (
            <>
              <p className="lead">{fmt(t.thermo_lead, { day: fmtDate(th.day, locale) })}</p>
              {th.day_events.length > 0 && <p className="notice">{fmt(DICT[locale === "en" ? "en" : "pt"].day_was_event, { names: th.day_events.map((e) => e.name).join(", ") })}</p>}
              <Thermo title={t.hot} rows={th.hot} t={t} locale={locale} boostedTag={DICT[locale === "en" ? "en" : "pt"].boosted_tag} />
              <Thermo title={t.cold} rows={th.cold} t={t} locale={locale} boostedTag={DICT[locale === "en" ? "en" : "pt"].boosted_tag} />
            </>
          )}
        </section>
      </div>

      <section className="card">
        <h2>{t.summary}</h2>
        <p className="lead">{t.summary_lead}</p>
        {r.raids.length === 0 ? <p className="muted">{fmt(t.none, { n: r.history_days })}</p> : (
          <div className="tbl"><table>
            <thead><tr><th>{t.raid}</th><th>{t.region}</th><th className="n">{t.count}</th><th>{t.last}</th><th className="n">{t.gap}</th><th>{t.next}</th></tr></thead>
            <tbody>
              {r.raids.map((s) => (
                <tr key={s.slug}>
                  <td>{s.name}</td><td>{s.region}</td><td className="n">{fmtNum(s.count, locale)}</td><td>{fmtDate(s.last, locale)}</td>
                  <td className="n">{s.median_gap_days ? `${s.median_gap_days} ${t.days_word}` : "–"}</td>
                  <td>{s.next_from ? `${fmtDate(s.next_from, locale)} – ${fmtDate(s.next_to, locale)}` : <span className="muted">{t.unknown}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
        <p className="muted" style={{ marginTop: 10 }}>{t.credit}</p>
      </section>
    </>
  );
}
