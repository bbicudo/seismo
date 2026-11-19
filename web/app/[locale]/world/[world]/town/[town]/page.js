import { notFound } from "next/navigation";
import { api, enc, fmtNum } from "../../../../../../lib/api";
import { dict, fmt } from "../../../../../../lib/i18n";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { world, town } = await params;
  return { title: `${decodeURIComponent(town)} · ${decodeURIComponent(world)}` };
}

function houseStatus(h, t) {
  if (h.auctioned) return <span className="pill off">{t.st_auction}</span>;
  if (h.rented) return <span className="pill on">{t.st_rented}</span>;
  return <span className="pill">{t.st_free}</span>;
}

export default async function Town({ params }) {
  const { locale, world, town } = await params;
  const t = dict(locale);
  const d = await api(`/v1/worlds/${enc(decodeURIComponent(world))}/towns/${enc(decodeURIComponent(town))}`);
  if (!d) notFound();
  const base = `/${locale}/world/${enc(d.world)}`;
  const rented = d.houses.filter((h) => h.rented).length;
  const auction = d.houses.filter((h) => h.auctioned).length;
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={`/${locale}`}>{t.nav_worlds}</a> / <a href={base}>{d.world}</a></p>
        <h1>{fmt(t.houses_in, { town: d.town })}</h1>
        <div className="stats">
          <div className="stat"><b>{fmtNum(d.houses.length, locale)}</b><span>{t.total}</span></div>
          <div className="stat"><b>{fmtNum(rented, locale)}</b><span>{t.rented}</span></div>
          <div className="stat"><b>{fmtNum(auction, locale)}</b><span>{t.auctioned}</span></div>
        </div>
      </section>
      <section className="card">
        <div className="tbl">
          <table>
            <thead>
              <tr><th>{t.house}</th><th>{t.status}</th><th>{t.owner}</th><th className="n">{t.size}</th><th className="n">{t.rent}</th><th className="n">{t.bid}</th><th>{t.time_left}</th></tr>
            </thead>
            <tbody>
              {d.houses.map((h) => (
                <tr key={h.house_id}>
                  <td><a href={`${base}/house/${h.house_id}`}>{h.name}</a>{h.kind === "guildhall" && <span className="muted"> · {t.kind_guildhall}</span>}</td>
                  <td>{houseStatus(h, t)}</td>
                  <td>{h.owner || (h.rented ? <span className="muted">{t.owner_unknown}</span> : "–")}</td>
                  <td className="n">{fmtNum(h.size, locale)}</td>
                  <td className="n">{fmtNum(h.rent, locale)}</td>
                  <td className="n">{h.auctioned ? fmtNum(h.current_bid || 0, locale) : "–"}</td>
                  <td>{h.time_left || "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
