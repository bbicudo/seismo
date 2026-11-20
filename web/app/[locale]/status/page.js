import { getFlags, on } from "../../../lib/flags";
import { notFound } from "next/navigation";
import { api, fmtNum, fmtTime } from "../../../lib/api";
import { dict } from "../../../lib/i18n";

export const dynamic = "force-dynamic";
export const metadata = { title: "Status" };

export default async function Status({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  if (!on(await getFlags(), "page_status")) notFound();
  const s = await api("/v1/status");
  const c = s.collector;
  return (
    <>
      <section className="card">
        <h1>{t.status_title}</h1>
        <p className="lead">
          {t.collector} <span className={`pill ${c.paused ? "off" : "on"}`}>{c.paused ? t.paused : t.collecting}</span>
          {" · "}{t.last_cycle} {fmtTime(c.last_cycle_at, locale)}
          {c.last_cycle_seconds != null && ` · ${c.last_cycle_seconds.toFixed(0)} s (${c.last_cycle_worlds})`}
        </p>
        <div className="stats">
          <div className="stat"><b>{fmtNum(c.requests_today_utc, locale)}</b><span>{t.requests_today}</span></div>
          <div className="stat"><b>{fmtNum(c.errors_today_utc, locale)}</b><span>{t.errors_today}</span></div>
          <div className="stat"><b>{fmtNum(s.database.characters, locale)}</b><span>{t.characters_seen}</span></div>
          <div className="stat"><b>{(s.database.db_bytes / 1e6).toFixed(0)} MB</b><span>{t.database}</span></div>
        </div>
      </section>
      <section className="card">
        <h2>{t.daily_jobs}</h2>
        <div className="tbl">
          <table>
            <thead><tr><th>{t.job}</th><th>{t.game_day}</th><th className="n">{t.items}</th><th className="n">{t.duration}</th><th>{t.finished}</th></tr></thead>
            <tbody>
              {["killstats", "guild_lists", "houses"].map((k) => {
                const j = s.daily_jobs[k];
                return (
                  <tr key={k}>
                    <td>{t[`job_${k}`]}</td><td>{j.day || t.waiting}</td><td className="n">{fmtNum(j.items, locale)}</td>
                    <td className="n">{j.seconds ? `${Math.max(1, Math.round(j.seconds / 60))} min` : "–"}</td>
                    <td>{fmtTime(j.finished_at, locale)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="muted">
          Guilds: {fmtNum(s.progress.guilds_read, locale)} / {fmtNum(s.progress.guilds, locale)} ·
          {" "}{t.house}: {fmtNum(s.progress.houses_read, locale)} / {fmtNum(s.progress.houses, locale)} ·
          {" "}kill statistics: {fmtNum(s.progress.kill_rows, locale)}
        </p>
      </section>
    </>
  );
}
