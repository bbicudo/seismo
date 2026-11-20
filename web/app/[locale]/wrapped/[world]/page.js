import { notFound } from "next/navigation";
import { api, enc, fmtNum } from "../../../../lib/api";
import { hours, monthLabel, validMonth, wt } from "../../../../lib/wrapped";
import ShareBar from "../../../../components/share-bar";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { world } = await params;
  return { title: `Wrapped · ${decodeURIComponent(world)}` };
}

function List({ title, rows, value }) {
  if (!rows.length) return null;
  return (
    <div>
      <h2 style={{ marginTop: 18 }}>{title}</h2>
      <div className="tbl"><table><tbody>
        {rows.map((r, i) => <tr key={r.race}><td>{i + 1}</td><td>{r.race}</td><td className="n">{value(r)}</td></tr>)}
      </tbody></table></div>
    </div>
  );
}

export default async function WrappedWorld({ params, searchParams }) {
  const { locale, world } = await params;
  const sp = await searchParams;
  const t = wt(locale);
  const month = validMonth(sp.month);
  const d = await api(`/v1/wrapped-world/${enc(decodeURIComponent(world))}${month ? `?month=${month}` : ""}`);
  if (!d) notFound();
  const nf = (n) => fmtNum(n, locale);
  return (
    <section className="card wrapped">
      <div className="kicker">Seismo Wrapped · {monthLabel(d.month, locale)}</div>
      <h1>{d.world}</h1>
      <p className="lead"><a href={`/${locale}/world/${enc(d.world)}`}>{t.world} →</a></p>
      {d.partial && <p className="notice">{t.partial}</p>}
      <div className="big">
        <div><b>{nf(d.avg_online)}</b><span>{t.avg_online}</span></div>
        <div><b>{nf(d.peak)}</b><span>{t.peak}</span></div>
        <div><b>{nf(d.deaths)}</b><span>{t.deaths}</span></div>
        <div><b>{nf(d.kills)}</b><span>{t.kills}</span></div>
        <div><b>{nf(d.new_characters)}</b><span>{t.new_chars}</span></div>
        <div><b>+{nf(d.levels_gained)}</b><span>{t.world_levels}</span></div>
        <div className="wide"><b>{nf(d.transfers.arrived)} / {nf(d.transfers.left)}</b><span>{t.arrived} / {t.left}</span></div>
      </div>
      <div className="grid2">
        <List title={t.top_creatures} rows={d.top_creatures} value={(r) => nf(r.killed)} />
        <List title={t.top_killers} rows={d.top_killers} value={(r) => nf(r.players_killed)} />
      </div>
      <ShareBar locale={locale} title={d.world} imagePath={`/${locale}/wrapped/${enc(d.world)}/opengraph-image`} />
    </section>
  );
}
