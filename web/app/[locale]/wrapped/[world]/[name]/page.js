import { getFlags, getParams, on } from "../../../../../lib/flags";
import { notFound } from "next/navigation";
import { api, enc, fmtNum } from "../../../../../lib/api";
import { fmt } from "../../../../../lib/i18n";
import { hours, monthLabel, validMonth, wt } from "../../../../../lib/wrapped";
import ShareBar from "../../../../../components/share-bar";
import { D, seo } from "../../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale, world, name } = await params;
  const sp = await getParams();
  const w = decodeURIComponent(world), n = decodeURIComponent(name);
  return seo(locale, `/wrapped/${encodeURIComponent(w)}/${encodeURIComponent(n)}`, { title: `Wrapped · ${n}`, description: D.wrappedChar[locale === "en" ? "en" : "pt"](n), noindex: !sp.seo_index_characters, ownImage: true });
}

export const dynamic = "force-dynamic";


export default async function WrappedCharacter({ params, searchParams }) {
  const { locale, world, name } = await params;
  const sp = await searchParams;
  const t = wt(locale);
  if (!on(await getFlags(), "page_wrapped")) notFound();
  const month = validMonth(sp.month);
  const d = await api(`/v1/wrapped/${enc(decodeURIComponent(world))}/${enc(decodeURIComponent(name))}${month ? `?month=${month}` : ""}`);
  if (!d) {
    return <section className="card"><h1>{t.title}</h1><p className="lead">{t.not_found}</p><p><a href={`/${locale}/wrapped`}>← {t.title}</a></p></section>;
  }
  const base = `/${locale}/wrapped/${enc(d.world)}`;
  return (
    <section className="card wrapped">
      <div className="kicker">Seismo Wrapped · {monthLabel(d.month, locale)}</div>
      <h1>{d.name}</h1>
      <p className="lead">
        <a href={`/${locale}/character/${enc(d.name)}`}>{d.vocation} · level {fmtNum(d.level, locale)}</a> · <a href={base}>{d.world}</a> ·{" "}
        {d.guild ? fmt(t.in_guild, { rank: d.guild.rank, guild: d.guild.name }) : t.no_guild}
      </p>
      {d.partial && <p className="notice">{t.partial}</p>}
      {d.minutes === 0 ? <p className="muted">{t.empty}</p> : (
        <div className="big">
          <div><b>{fmtNum(hours(d.minutes), locale)}</b><span>{t.hours}</span></div>
          <div><b>{fmtNum(d.days_active, locale)}</b><span>{t.days}</span><small>{fmtNum(hours(d.best_day_minutes), locale)} h {t.best_day}</small></div>
          <div><b>+{fmtNum(d.levels_gained, locale)}</b><span>{t.levels}</span>{d.level_start && <small>{d.level_start} → {d.level_end}</small>}</div>
          {d.top_percent && <div><b>{fmt(t.top_of, { p: d.top_percent })}</b><span>{t.top}</span><small>{fmtNum(d.world_players, locale)} {t.character.toLowerCase()}s</small></div>}
          {d.favorite_weekday && <div><b style={{ fontSize: 26 }}>{t.weekdays[d.favorite_weekday]}</b><span>{t.fav_day}</span></div>}
        </div>
      )}
      <ShareBar locale={locale} title={d.name} imagePath={`/${locale}/wrapped/${enc(d.world)}/${enc(d.name)}/opengraph-image`} />
    </section>
  );
}
