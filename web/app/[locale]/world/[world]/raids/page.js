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
    lead: "Raids que aconteceram neste mundo e quando a próxima deve vir.",
    recent: "Raids recentes",
    none: "Nenhuma raid detectada ainda.",
    raid: "Raid",
    region: "Região",
    day: "Dia",
    kills: "Mortes",
    summary: "Frequência e próxima janela",
    count: "Vezes",
    last: "Última",
    gap: "Intervalo típico",
    next: "Próxima janela provável",
    days_word: "dias",
    unknown: "poucos dados",
    in_window: "na janela",
    overdue: "atrasada",
    detectable: "Acompanhamos {d} das {t} raids conhecidas.",
    thermo: "Termômetro de respawn",
    thermo_lead: "Criaturas mortas em {day} comparadas à média dos 28 dias anteriores.",
    thermo_wait: "O termômetro aparece com {n} dias de histórico.",
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
    lead: "Raids that happened in this world and when the next one is likely.",
    recent: "Recent raids",
    none: "No raids detected yet.",
    raid: "Raid",
    region: "Region",
    day: "Day",
    kills: "Kills",
    summary: "Frequency and next window",
    count: "Times",
    last: "Last",
    gap: "Typical gap",
    next: "Likely next window",
    days_word: "days",
    unknown: "not enough data",
    in_window: "in window",
    overdue: "overdue",
    detectable: "We track {d} of the {t} known raids.",
    thermo: "Respawn thermometer",
    thermo_lead: "Creatures killed on {day} compared with the previous 28-day average.",
    thermo_wait: "The thermometer shows up with {n} days of history.",
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
  const today = new Date().toISOString().slice(0, 10);
  return (
    <>
      <section className="card">
        <h2>{t.summary}</h2>
        <p className="lead">{t.lead}</p>
        {r.raids.length === 0 ? <p className="muted">{fmt(t.none, { n: r.history_days })}</p> : (
          <div className="tbl"><table>
            <thead><tr><th>{t.raid}</th><th>{t.region}</th><th className="n">{t.count}</th><th>{t.last}</th><th className="n">{t.gap}</th><th>{t.next}</th></tr></thead>
            <tbody>
              {r.raids.map((s) => (
                <tr key={s.slug}>
                  <td>{s.name}</td><td>{s.region}</td><td className="n">{fmtNum(s.count, locale)}</td><td>{fmtDate(s.last, locale)}</td>
                  <td className="n">{s.median_gap_days ? `${s.median_gap_days} ${t.days_word}` : "–"}</td>
                  <td>{s.next_from ? <>{`${fmtDate(s.next_from, locale)} – ${fmtDate(s.next_to, locale)}`}
                    {today >= s.next_from && today <= s.next_to && <> <span className="pill on">{t.in_window}</span></>}
                    {today > s.next_to && <> <span className="pill off">{t.overdue}</span></>}</> : <span className="muted">{t.unknown}</span>}</td>
                </tr>
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

      <p className="muted">{fmt(t.detectable, { d: r.detectable, t: r.total })} {t.credit}</p>
    </>
  );
}
