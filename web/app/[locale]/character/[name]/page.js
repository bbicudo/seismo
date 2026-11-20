import { notFound } from "next/navigation";
import { DayBars } from "../../../../components/charts";
import { api, enc, fmtDate, fmtNum } from "../../../../lib/api";
import { getFlags, on } from "../../../../lib/flags";
import { fmt } from "../../../../lib/i18n";
import { D, seo } from "../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale, name } = await params;
  const n = decodeURIComponent(name);
  return seo(locale, `/character/${encodeURIComponent(n)}`, { title: n, description: D.character[locale === "en" ? "en" : "pt"](n), noindex: true });
}

export const dynamic = "force-dynamic";

const T = {
  pt: {
    level: "level atual", world: "Mundo", since: "visto pela primeira vez", last: "último dia visto",
    hours30: "horas online (30 dias)", days30: "dias jogados (30 dias)", no_guild: "sem guild",
    in_guild: "{rank} na {guild}", daily: "Horas online por dia", daily_lead: "Total de cada dia de jogo nos últimos {n} dias. O Seismo não guarda horários de login, só a soma do dia.",
    no_daily: "Ainda não há minutos registrados.", months: "Levels por mês", month: "Mês", from: "Início", to: "Fim", gained: "Ganho",
    no_months: "Nenhuma mudança de level registrada ainda.", houses: "Casas", no_houses: "Nenhuma casa registrada no nome.",
    transfers: "Transfers", no_transfers: "Nenhum transfer detectado.", day: "Dia", wrapped: "Wrapped do mês →",
    guild: "Guild", optout: "É seu e não quer aparecer aqui? Faça o opt-out.",
    days_opts: "Período:",
    not_seen: "Este personagem ainda não foi visto online pelo Seismo. Os dados abaixo vêm da guild.",
  },
  en: {
    level: "current level", world: "World", since: "first seen", last: "last day seen",
    hours30: "hours online (30 days)", days30: "days played (30 days)", no_guild: "no guild",
    in_guild: "{rank} of {guild}", daily: "Hours online per day", daily_lead: "Total for each game day over the last {n} days. Seismo stores no login times, only the daily sum.",
    no_daily: "No minutes recorded yet.", months: "Levels per month", month: "Month", from: "Start", to: "End", gained: "Gained",
    no_months: "No level changes recorded yet.", houses: "Houses", no_houses: "No houses recorded under this name.",
    transfers: "Transfers", no_transfers: "No transfers detected.", day: "Day", wrapped: "Monthly Wrapped →",
    guild: "Guild", optout: "Is this yours and you would rather not be listed? Use the opt-out.",
    days_opts: "Period:",
    not_seen: "Seismo has not seen this character online yet. The data below comes from the guild.",
  },
};


export default async function Character({ params, searchParams }) {
  const { locale, name } = await params;
  const sp = await searchParams;
  const t = T[locale] || T.pt;
  const days = [30, 60, 120].includes(Number(sp.days)) ? Number(sp.days) : 60;
  const [c, f] = await Promise.all([api(`/v1/characters/${enc(decodeURIComponent(name))}?days=${days}`), getFlags()]);
  if (!c) notFound();
  const nf = (n) => fmtNum(n, locale);
  const today = new Date().toISOString().slice(0, 10);
  // o gráfico começa no primeiro dia em que o personagem foi visto, para as barras não ficarem espremidas
  const windowStart = new Date(Date.now() - (days - 1) * 864e5).toISOString().slice(0, 10);
  const from = c.first_seen_day && c.first_seen_day > windowStart ? c.first_seen_day : windowStart;
  const short = (d) => (d ? new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "pt-BR", { dateStyle: "short", timeZone: "UTC" }).format(new Date(`${d}T12:00:00Z`)) : "–");
  const points = c.daily.map((d) => ({ day: d.day, v: Math.round(d.minutes / 6) / 10 }));
  const wbase = `/${locale}/world/${enc(c.world)}`;
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={wbase}>{c.world}</a></p>
        <h1>{c.name}</h1>
        <p className="lead">
          {c.vocation} · <a href={wbase}>{c.world}</a> ({c.location}, {c.pvp_type}) ·{" "}
          {c.guild ? (on(f, "page_guilds")
            ? <a href={`/${locale}/world/${enc(c.guild.world)}/guild/${enc(c.guild.name)}`}>{fmt(t.in_guild, { rank: c.guild.rank, guild: c.guild.name })}</a>
            : fmt(t.in_guild, { rank: c.guild.rank, guild: c.guild.name })) : t.no_guild}
          {on(f, "page_wrapped") && c.seen_online && <> · <a href={`/${locale}/wrapped/${enc(c.world)}/${enc(c.name)}`}>{t.wrapped}</a></>}
        </p>
        {!c.seen_online && <p className="notice">{t.not_seen}</p>}
        <div className="stats">
          <div className="stat"><b>{nf(c.level)}</b><span>{t.level}</span></div>
          {c.seen_online && <>
            <div className="stat"><b>{nf(Math.round(c.minutes_30d / 6) / 10)}</b><span>{t.hours30}</span></div>
            <div className="stat"><b>{nf(c.active_days_30d)}</b><span>{t.days30}</span></div>
            <div className="stat"><b>{short(c.first_seen_day)}</b><span>{t.since}</span></div>
            <div className="stat"><b>{short(c.last_seen_day)}</b><span>{t.last}</span></div>
          </>}
        </div>
      </section>

      <section className="card">
        <h2>{t.daily}</h2>
        <p className="lead">
          {fmt(t.daily_lead, { n: days })}{" "}
          <span className="muted">{t.days_opts}</span>{" "}
          {[30, 60, 120].map((d) => (
            <a key={d} href={`/${locale}/character/${enc(c.name)}?days=${d}`} style={{ marginRight: 8, fontWeight: d === days ? 700 : 400 }}>{d}d</a>
          ))}
        </p>
        {points.length === 0 ? <p className="muted">{t.no_daily}</p> : <DayBars points={points} from={from} to={today} locale={locale} label={t.daily} />}
      </section>

      <div className="grid2">
        <section className="card">
          <h2>{t.months}</h2>
          {c.months.length === 0 ? <p className="muted">{t.no_months}</p> : (
            <div className="tbl"><table>
              <thead><tr><th>{t.month}</th><th className="n">{t.from}</th><th className="n">{t.to}</th><th className="n">{t.gained}</th></tr></thead>
              <tbody>
                {c.months.map((m) => (
                  <tr key={m.month}>
                    <td>{new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "pt-BR", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${m.month}T12:00:00Z`))}</td>
                    <td className="n">{nf(m.level_start)}</td><td className="n">{nf(m.level_end)}</td>
                    <td className="n">{m.level_end - m.level_start >= 0 ? "+" : ""}{nf(m.level_end - m.level_start)}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </section>
        <section className="card">
          <h2>{t.houses}</h2>
          {c.houses.length === 0 ? <p className="muted">{t.no_houses}</p> : (
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {c.houses.map((h) => (
                <li key={h.house_id}>
                  {on(f, "page_houses") ? <a href={`/${locale}/world/${enc(h.world)}/house/${h.house_id}`}>{h.name}</a> : h.name}
                  <span className="muted"> · {h.town} · {t.since} {fmtDate(h.first_seen_day, locale)}</span>
                </li>
              ))}
            </ul>
          )}
          <h2 style={{ marginTop: 18 }}>{t.transfers}</h2>
          {c.transfers.length === 0 ? <p className="muted">{t.no_transfers}</p> : (
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {c.transfers.map((x) => <li key={x.day + x.to_world}>{fmtDate(x.day, locale)}: {x.from_world} → {x.to_world}</li>)}
            </ul>
          )}
        </section>
      </div>
      <p className="muted"><a href={`/${locale}/opt-out?name=${enc(c.name)}`}>{t.optout}</a></p>
    </>
  );
}
