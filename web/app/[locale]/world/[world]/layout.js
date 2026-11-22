import { notFound } from "next/navigation";
import WorldTabs from "../../../../components/world-tabs";
import { api, enc, fmtNum, fmtTime } from "../../../../lib/api";
import { getFlags, on } from "../../../../lib/flags";
import { dict, fmt } from "../../../../lib/i18n";
import { it } from "../../../../lib/insights-i18n";

// Cabeçalho e abas comuns a todas as páginas de um mundo. Cada aba traz só o seu assunto,
// para nenhuma página ficar longa demais e nenhuma informação aparecer em dois lugares.
export default async function WorldLayout({ children, params }) {
  const { locale, world } = await params;
  const [w, f] = await Promise.all([api(`/v1/worlds/${enc(decodeURIComponent(world))}/summary`), getFlags()]);
  if (!w) notFound();
  const t = dict(locale);
  const x = it(locale);
  const base = `/${locale}/world/${enc(w.name)}`;
  const h = w.health;
  const tabs = [
    { href: base, label: x.tab_overview, match: [""] },
    (on(f, "page_heatmap") || on(f, "page_vocations") || on(f, "page_funnel") || on(f, "page_retention") || on(f, "page_leveling"))
      && { href: `${base}/activity`, label: x.tab_activity, match: ["activity"] },
    on(f, "page_hunts") && { href: `${base}/hunts`, label: x.tab_hunts, match: ["hunts"] },
    on(f, "page_raids") && { href: `${base}/raids`, label: x.tab_raids, match: ["raids"] },
    on(f, "page_guilds") && { href: `${base}/guilds`, label: x.tab_guilds, match: ["guilds", "guild"] },
    on(f, "page_houses") && { href: `${base}/houses`, label: x.tab_houses, match: ["houses", "town", "house"] },
  ].filter(Boolean);
  return (
    <>
      <section className="card world-head">
        <p className="crumbs"><a href={`/${locale}`}>← {t.back_worlds}</a></p>
        <h1>{w.name}</h1>
        <p className="lead">
          {w.location} · {w.pvp_type}{w.battleye_protected ? ` · BattlEye${w.battleye_type ? ` ${w.battleye_type}` : ""}` : ""} · {fmt(x.updated, { t: fmtTime(w.updated_at, locale) })}
        </p>
        <div className="stats">
          <div className="stat"><b>{fmtNum(w.players_online, locale)}</b><span>{t.online_now}</span></div>
          <div className="stat"><b>{fmtNum(w.record?.players_online, locale)}</b><span>{t.record}</span></div>
          {h && on(f, "page_health_index") && (
            <div className="stat">
              {h.score != null
                ? <><b>{h.score}<small>/100</small></b><span>{x.health_score} · {fmt(x.health_rank, { r: h.rank, n: h.total })}</span></>
                : <><b className="soft">{x.health_wait}</b><span>{x.health_score} · {fmt(x.health_wait_days, { d: Math.max(1, Math.ceil(h.days_needed - h.days_collected)) })}</span></>}
            </div>
          )}
        </div>
        <WorldTabs base={base} tabs={tabs} label={x.tabs_label}
                   extra={on(f, "page_wrapped") ? { href: `/${locale}/wrapped/${enc(w.name)}`, label: "Wrapped →" } : null} />
      </section>
      {children}
    </>
  );
}
