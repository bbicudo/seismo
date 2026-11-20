import { notFound } from "next/navigation";
import { Bars, TimeChart } from "../../../../components/charts";
import { api, enc, fmtDate, fmtNum } from "../../../../lib/api";
import { getFlags, on } from "../../../../lib/flags";
import { dict, fmt } from "../../../../lib/i18n";
import { it, signed, trendClass } from "../../../../lib/insights-i18n";
import { D, seo } from "../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale, world } = await params;
  const w = decodeURIComponent(world);
  return seo(locale, `/world/${encodeURIComponent(w)}`, { title: w, description: D.world[locale === "en" ? "en" : "pt"](w) });
}

export const dynamic = "force-dynamic";

// Visão geral: como o mundo está (sinais vitais), como o online se comportou e para onde vão os transfers.
export default async function World({ params, searchParams }) {
  const { locale, world } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const x = it(locale);
  const name = decodeURIComponent(world);
  const days = [7, 14, 30].includes(Number(sp.days)) ? Number(sp.days) : 14;
  const f = await getFlags();
  const [s, health, flows] = await Promise.all([
    api(`/v1/worlds/${enc(name)}/summary`),
    on(f, "page_health") ? api(`/v1/worlds/${enc(name)}/health?days=${days}`) : null,
    on(f, "page_transfer_flows") ? api(`/v1/worlds/${enc(name)}/flows`) : null,
  ]);
  if (!s) notFound();
  const base = `/${locale}/world/${enc(s.name)}`;
  const h = s.health;
  const nf = (n, d = 0) => (n == null ? "–" : new Intl.NumberFormat(locale === "en" ? "en-GB" : "pt-BR", { maximumFractionDigits: d }).format(n));
  const need = fmt(x.v_need, { n: h?.days_needed });
  const vitals = h && on(f, "page_health_index") ? [
    { v: h.trend_pct, show: signed(h.trend_pct, locale, 1), label: x.v_trend, cls: trendClass(h.trend_pct) },
    { v: h.retention_pct, show: h.retention_pct == null ? null : `${nf(h.retention_pct, 1)}%`, label: x.v_retention },
    { v: h.new_per_1k, show: nf(h.new_per_1k, 1), label: x.v_new },
    { v: h.net_transfers_per_1k, show: signed(h.net_transfers_per_1k, locale, 1, ""), label: x.v_transfers, cls: trendClass(h.net_transfers_per_1k) },
  ] : null;
  const points = health ? health.hourly.map((p) => ({ t: p.hour, v: p.avg, peak: p.max })) : [];
  return (
    <>
      {vitals && (
        <section className="card">
          <h2>{x.vitals}</h2>
          <p className="lead">
            {h.ready ? fmt(x.vitals_lead, { w: h.window }) : fmt(x.vitals_wait, { n: h.days_needed, d: nf(h.days_collected, 1) })}
          </p>
          <div className="stats">
            {vitals.map((v) => (
              <div className="stat" key={v.label}>
                {v.v == null ? <b className="soft">{need}</b> : <b className={v.cls}>{v.show}</b>}
                <span>{v.label}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {health && (
        <section className="card">
          <h2>{t.health}</h2>
          <p className="lead">
            {fmt(t.health_lead, { days })}{" "}
            <span className="seg">
              {[7, 14, 30].map((d) => (
                <a key={d} href={`${base}?days=${d}`} aria-current={d === days ? "true" : undefined}>{d}d</a>
              ))}
            </span>
          </p>
          <TimeChart points={points} locale={locale} label={fmt(t.health_lead, { days })} peakLabel={t.peak} shade={health.event_days} />
          <div className="legend"><span><i />{t.avg}</span><span><i className="dash" />{t.peak}</span>{health.event_days.length > 0 && <span><i className="box" />{t.event_days_legend}</span>}</div>
          <p className="muted" style={{ marginTop: 8 }}>{fmt(t.collecting_since, { date: fmtDate(health.collecting_since, locale) })}</p>
        </section>
      )}

      {flows && (
        <section className="card">
          <h2>{x.flows}</h2>
          <p className="lead">{fmt(x.flows_lead, { d: flows.days })}</p>
          <div className="grid-even">
            <div>
              <h3 className="sub">{x.flows_in} <b>{fmtNum(flows.arrived_total, locale)}</b></h3>
              {flows.arrived.length === 0 ? <p className="muted">{x.flows_none}</p>
                : <Bars rows={flows.arrived.map((r) => ({ label: r.world, href: `/${locale}/world/${enc(r.world)}`, v: r.n }))} locale={locale} />}
            </div>
            <div>
              <h3 className="sub">{x.flows_out} <b>{fmtNum(flows.left_total, locale)}</b></h3>
              {flows.left.length === 0 ? <p className="muted">{x.flows_none}</p>
                : <Bars rows={flows.left.map((r) => ({ label: r.world, href: `/${locale}/world/${enc(r.world)}`, v: r.n }))} locale={locale} tone="out" />}
            </div>
          </div>
        </section>
      )}
    </>
  );
}
