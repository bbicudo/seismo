import { notFound } from "next/navigation";
import { api, enc, fmtNum } from "../../../../../../lib/api";
import { hours, monthLabel, validMonth, wt } from "../../../../../../lib/wrapped";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { guild } = await params;
  return { title: `Wrapped · ${decodeURIComponent(guild)}` };
}

export default async function WrappedGuild({ params, searchParams }) {
  const { locale, world, guild } = await params;
  const sp = await searchParams;
  const t = wt(locale);
  const month = validMonth(sp.month);
  const d = await api(`/v1/wrapped-guild/${enc(decodeURIComponent(world))}/${enc(decodeURIComponent(guild))}${month ? `?month=${month}` : ""}`);
  if (!d) notFound();
  const nf = (n) => fmtNum(n, locale);
  return (
    <section className="card wrapped">
      <div className="kicker">Seismo Wrapped · {monthLabel(d.month, locale)}</div>
      <h1>{d.guild}</h1>
      <p className="lead">
        <a href={`/${locale}/wrapped/${enc(d.world)}`}>{d.world}</a> ·{" "}
        <a href={`/${locale}/world/${enc(d.world)}/guild/${enc(d.guild)}`}>{t.guild} →</a>
      </p>
      {d.partial && <p className="notice">{t.partial}</p>}
      <div className="big">
        <div><b>{nf(d.members_total)}</b><span>{t.guild}</span></div>
        <div><b>{nf(d.active_members)}</b><span>{t.active}</span></div>
        <div><b>{nf(hours(d.minutes))}</b><span>{t.member_hours}</span></div>
        <div><b>+{nf(d.levels_gained)}</b><span>{t.levels}</span></div>
        <div><b>{nf(d.joins)} / {nf(d.leaves)}</b><span>{t.joins} / {t.leaves}</span></div>
      </div>
      {d.top_levels.length > 0 && (
        <>
          <h2 style={{ marginTop: 18 }}>{t.top_levelers}</h2>
          <div className="tbl"><table><tbody>
            {d.top_levels.map((m, i) => (
              <tr key={m.name}>
                <td>{i + 1}</td>
                <td><a href={`/${locale}/wrapped/${enc(d.world)}/${enc(m.name)}`}>{m.name}</a></td>
                <td className="n">+{nf(m.gained)}</td><td className="n">{nf(m.level_end)}</td>
              </tr>
            ))}
          </tbody></table></div>
        </>
      )}
      <p className="muted" style={{ marginTop: 16 }}>{t.share}</p>
    </section>
  );
}
