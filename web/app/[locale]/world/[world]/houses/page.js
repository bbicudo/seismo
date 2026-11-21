import { notFound } from "next/navigation";
import { api, enc, fmtNum } from "../../../../../lib/api";
import { dict, fmt } from "../../../../../lib/i18n";
import { it } from "../../../../../lib/insights-i18n";
import { seo } from "../../../../../lib/seo";

const DESC = {
  pt: (w) => `Mercado de casas de ${w}: ocupação por cidade, leilões abertos, lances, tempo até alugar e trocas de dono.`,
  en: (w) => `${w} house market: occupancy by town, open auctions, bids, time to rent and owner changes.`,
};

export async function generateMetadata({ params }) {
  const { locale, world } = await params;
  const w = decodeURIComponent(world);
  const x = it(locale);
  return seo(locale, `/world/${encodeURIComponent(w)}/houses`, { title: `${x.tab_houses} · ${w}`, description: DESC[locale === "en" ? "en" : "pt"](w) });
}

export const dynamic = "force-dynamic";

export default async function Houses({ params }) {
  const { locale, world } = await params;
  const t = dict(locale);
  const x = it(locale);
  const d = await api(`/v1/worlds/${enc(decodeURIComponent(world))}/houses`);
  if (!d) notFound();
  const base = `/${locale}/world/${enc(d.world)}`;
  const tot = d.totals;
  const nf = (n) => fmtNum(n, locale);
  const nf1 = (n) => (n == null ? "–" : new Intl.NumberFormat(locale === "en" ? "en-GB" : "pt-BR", { maximumFractionDigits: 1 }).format(n));
  return (
    <>
      <section className="card">
        <h2>{x.houses_title}</h2>
        <p className="lead">{fmt(x.houses_lead, { w: d.window })}</p>
        {d.towns.length === 0 ? <p className="muted">{t.not_yet}</p> : (
          <div className="stats">
            <div className="stat"><b>{nf(tot.total)}</b><span>{x.h_total}</span></div>
            <div className="stat"><b>{tot.occupancy_pct == null ? "–" : `${tot.occupancy_pct}%`}</b><span>{x.h_occupancy}</span></div>
            <div className="stat"><b>{nf(tot.auctioned)}</b><span>{x.h_auctioned}</span></div>
            <div className="stat"><b>{nf(tot.closed)}</b><span>{x.h_closed}</span></div>
            <div className="stat"><b>{nf1(d.median_days)}</b><span>{x.h_days}</span></div>
          </div>
        )}
        <p className="muted" style={{ marginTop: 10 }}>{fmt(x.houses_hist, { n: d.history_days, r: nf(tot.owners_read), t: nf(tot.total) })}</p>
      </section>

      {d.towns.length > 0 && (
        <section className="card">
          <div className="tbl"><table className="compact cards">
            <thead><tr>
              <th>{x.town}</th><th className="n">{t.total}</th><th className="n">{x.occupancy}</th><th className="n">{x.auctioned}</th>
              <th className="n">{x.avg_bid}</th><th className="n">{x.closed}</th><th className="n">{x.owner_changes}</th>
            </tr></thead>
            <tbody>
              {d.towns.map((h) => (
                <tr key={h.town}>
                  <td className="place"><a href={`${base}/town/${enc(h.town)}`}>{h.town}</a></td>
                  <td className="n">{nf(h.total)}</td>
                  <td className="n"><span className="meter" style={{ "--p": `${h.occupancy_pct ?? 0}%` }}>{h.occupancy_pct == null ? "–" : `${h.occupancy_pct}%`}</span></td>
                  <td className="n">{nf(h.auctioned)}</td>
                  <td className="n">{h.avg_bid ? nf(h.avg_bid) : "–"}</td>
                  <td className="n">{nf(h.closed)}</td>
                  <td className="n">{nf(h.owner_changes)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </section>
      )}
    </>
  );
}
