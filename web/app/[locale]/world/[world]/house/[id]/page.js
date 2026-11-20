import { notFound } from "next/navigation";
import { api, enc, fmtDate, fmtNum } from "../../../../../../lib/api";
import { dict } from "../../../../../../lib/i18n";
import { D, seo } from "../../../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale, world, id } = await params;
  const w = decodeURIComponent(world);
  return seo(locale, `/world/${encodeURIComponent(w)}/house/${id}`, { title: `House ${id} · ${w}`, description: D.house[locale === "en" ? "en" : "pt"](`House ${id}`, w) });
}

export const dynamic = "force-dynamic";

export default async function House({ params }) {
  const { locale, world, id } = await params;
  const t = dict(locale);
  if (!/^\d+$/.test(id)) notFound();
  const h = await api(`/v1/worlds/${enc(decodeURIComponent(world))}/houses/${id}`);
  if (!h) notFound();
  const base = `/${locale}/world/${enc(h.world)}`;
  const now = h.history[0];
  const current = h.owners.find((o) => !o.ended_day);
  return (
    <>
      <section className="card">
        <p className="crumbs">
          <a href={`/${locale}`}>{t.nav_worlds}</a> / <a href={base}>{h.world}</a> / <a href={`${base}/town/${enc(h.town)}`}>{h.town}</a>
        </p>
        <h1>{h.name}</h1>
        <p className="lead">{h.kind === "guildhall" ? t.kind_guildhall : t.kind_house} · {h.town}</p>
        <div className="stats">
          <div className="stat"><b>{now ? (now.auctioned ? t.st_auction : now.rented ? t.st_rented : t.st_free) : "–"}</b><span>{t.status}</span></div>
          <div className="stat"><b>{current?.owner || "–"}</b><span>{t.owner}</span></div>
          <div className="stat"><b>{fmtNum(h.size, locale)}</b><span>{t.size}</span></div>
          <div className="stat"><b>{fmtNum(h.rent, locale)}</b><span>{t.rent}</span></div>
          <div className="stat"><b>{fmtNum(h.beds, locale)}</b><span>{t.beds}</span></div>
        </div>
      </section>
      <div className="grid2">
        <section className="card">
          <h2>{t.history}</h2>
          <div className="tbl">
            <table>
              <thead><tr><th>{t.day}</th><th>{t.status}</th><th className="n">{t.bid}</th><th>{t.time_left}</th></tr></thead>
              <tbody>
                {h.history.map((s) => (
                  <tr key={s.snap_day}>
                    <td>{fmtDate(s.snap_day, locale)}</td>
                    <td>{s.auctioned ? t.st_auction : s.rented ? t.st_rented : t.st_free}</td>
                    <td className="n">{s.auctioned ? fmtNum(s.current_bid || 0, locale) : "–"}</td>
                    <td>{s.time_left || "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="card">
          <h2>{t.owners_history}</h2>
          {h.owners.length === 0 ? <p className="muted">{t.owner_unknown}</p> : (
            <div className="tbl">
              <table>
                <thead><tr><th>{t.owner}</th><th>{t.from}</th><th>{t.until}</th></tr></thead>
                <tbody>
                  {h.owners.map((o) => (
                    <tr key={o.owner + o.first_seen_day}>
                      <td><a href={`/${locale}/character/${enc(o.owner)}`}>{o.owner}</a></td><td>{fmtDate(o.first_seen_day, locale)}</td>
                      <td>{o.ended_day ? fmtDate(o.ended_day, locale) : <span className="pill on">{t.current}</span>}</td>
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
