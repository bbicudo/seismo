import { notFound } from "next/navigation";
import ElementIcon from "../../../../../components/element-icon";
import data from "../../../../../data/hunt-areas.json";
import { fmtDate, fmtNum } from "../../../../../lib/api";
import { getFlags, on } from "../../../../../lib/flags";
import { ATTACK, ICON_CDN, advise } from "../../../../../lib/hunt-advice";
import { EL, ht } from "../../../../../lib/hunts-i18n";
import { dict, fmt } from "../../../../../lib/i18n";
import { seo } from "../../../../../lib/seo";

const BY_SLUG = new Map(data.areas.map((a) => [a.slug, a]));
const sprite = (c) => (c?.img ? `${ICON_CDN}${c.img}&path-prefix=en` : null);
const wiki = (name) => `https://tibia.fandom.com/wiki/${encodeURIComponent(name.replace(/ /g, "_"))}`;
const Stars = ({ n }) => <b>{"★".repeat(n)}<span className="soft">{"★".repeat(Math.max(0, 5 - n))}</span></b>;

export async function generateMetadata({ params }) {
  const { locale, slug } = await params;
  const a = BY_SLUG.get(slug);
  const t = ht(locale);
  if (!a) return {};
  const adv = advise(a, data.creatures);
  const best = adv.bestElement ? fmt(adv.bestElement.avg > 100 ? t.attack_best : t.attack_flat, { e: EL[adv.bestElement.e], n: adv.bestElement.avg }) : "";
  return seo(locale, `/utils/hunts/${slug}`, {
    title: `${a.name} · ${t.title}`,
    description: [a.city, a.creatures.slice(0, 6).join(", "), best].filter(Boolean).join(" · "),
  });
}

export const dynamic = "force-dynamic";

function Monster({ name, icons, locale }) {
  const c = data.creatures[name];
  const hits = Object.entries(c.dmg || {}).sort((a, b) => b[1] - a[1]);
  return (
    <tr>
      <td className="place">
        <span className="item-name">
          {sprite(c) ? <img src={sprite(c)} alt="" width={32} height={32} loading="lazy" referrerPolicy="no-referrer" /> : <i className="item-noimg" />}
          <span><a href={wiki(name)} target="_blank" rel="noopener noreferrer">{name}</a></span>
        </span>
      </td>
      <td className="n">{c.hp ? fmtNum(c.hp, locale) : "–"}</td>
      <td className="n">{c.exp ? fmtNum(c.exp, locale) : "–"}</td>
      {ATTACK.map((e) => {
        const v = c.mods[e];
        return <td key={e} className={`n ${v > 100 ? "up" : v < 100 ? "down" : ""}`}>{v == null ? "–" : `${v}%`}</td>;
      })}
      <td className={hits.length ? "" : "empty"}>
        {hits.length ? <span className="el-list">{hits.map(([e]) => <ElementIcon key={e} e={e} icons={icons} />)}</span> : "–"}
      </td>
    </tr>
  );
}

export default async function HuntArea({ params }) {
  const { locale, slug } = await params;
  const f = await getFlags();
  if (!on(f, "page_utils") || !on(f, "util_hunts")) notFound();
  const a = BY_SLUG.get(slug);
  if (!a) notFound();
  const t = ht(locale);
  const adv = advise(a, data.creatures);
  const icons = data.icons;
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={`/${locale}/utils/hunts`}>← {t.back}</a></p>
        <h1>{a.name}</h1>
        <p className="lead">
          {a.city && <>{a.city} · </>}
          <a href={wiki(a.name)} target="_blank" rel="noopener noreferrer">{t.wiki} ↗</a>
        </p>
        <div className="stats">
          {Object.entries(a.lvl || {}).map(([k, v]) => <div className="stat" key={k}><b>{v}</b><span>{t.levels} · {t.voc[k]}</span></div>)}
          {a.exp ? <div className="stat"><Stars n={a.exp} /><span>{t.exp}</span></div> : null}
          {a.loot ? <div className="stat"><Stars n={a.loot} /><span>{t.loot}</span></div> : null}
        </div>
      </section>

      <div className="grid-even">
        <section className="card">
          <h2>{t.attack_title}</h2>
          <p className="lead">{t.attack_lead}</p>
          {adv.bestElement && <p className="advice">{fmt(adv.bestElement.avg > 100 ? t.attack_best : t.attack_flat, { e: EL[adv.bestElement.e], n: adv.bestElement.avg })}</p>}
          {adv.physical && <p className="muted">{fmt(t.attack_physical, { n: adv.physical.avg })}</p>}
          <ul className="el-bars">
            {adv.attack.map((x) => (
              <li key={x.e} title={fmt(t.attack_range, { min: x.min, max: x.max })}>
                <ElementIcon e={x.e} icons={icons} />
                <span className="bt"><i style={{ width: `${Math.min(100, (x.avg / 150) * 100)}%` }} className={x.avg > 100 ? "good" : x.avg < 100 ? "bad" : ""} /></span>
                <span className="bv">{x.avg}%</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2>{t.protect_title}</h2>
          <p className="lead">{t.protect_lead}</p>
          {adv.protect.length === 0 ? <p className="muted">{t.protect_none}</p> : (
            <>
              {adv.protectTop.length > 0 && <p className="advice">{fmt(t.protect_best, { list: adv.protectTop.map((x) => EL[x.e]).join(", ") })}</p>}
              <ul className="el-bars">
                {adv.protect.map((x) => (
                  <li key={x.e} title={fmt(t.protect_hit, { n: fmtNum(x.hit, locale) })}>
                    <ElementIcon e={x.e} icons={icons} />
                    <span className="bt"><i style={{ width: `${x.pct}%` }} /></span>
                    <span className="bv">{x.pct}%</span>
                  </li>
                ))}
              </ul>
              {adv.unknownDamage.length > 0 && <p className="muted" style={{ marginTop: 8 }}>{fmt(t.unknown, { list: adv.unknownDamage.join(", ") })}</p>}
            </>
          )}
        </section>
      </div>

      <section className="card">
        <h2>{t.monsters_title}</h2>
        <p className="muted">{t.legend}</p>
        <div className="tbl"><table className="compact cards">
          <thead><tr>
            <th>{t.monster}</th><th className="n">{t.hp}</th><th className="n">{t.xp}</th>
            {ATTACK.map((e) => <th key={e} className="n">{EL[e]}</th>)}
            <th>{t.hits}</th>
          </tr></thead>
          <tbody>{a.creatures.map((n) => <Monster key={n} name={n} icons={icons} locale={locale} />)}</tbody>
        </table></div>
        {a.bosses.length > 0 && (
          <>
            <h3 className="sub" style={{ marginTop: 16 }}>{t.bosses}</h3>
            <p className="boss-list">
              {a.bosses.map((n) => (
                <a key={n} href={wiki(n)} target="_blank" rel="noopener noreferrer" className="boss">
                  {sprite(data.creatures[n]) && <img src={sprite(data.creatures[n])} alt="" width={32} height={32} loading="lazy" referrerPolicy="no-referrer" />}
                  {n}
                </a>
              ))}
            </p>
          </>
        )}
      </section>
      {on(f, "feedback_form") && (
        <p className="muted"><a href={`/${locale}/feedback?f=hunts&from=/${locale}/utils/hunts/${slug}`}>{dict(locale).fb_link}</a></p>
      )}
      <p className="muted">{fmt(t.credit, { d: fmtDate(data.updated, locale) })}</p>
    </>
  );
}
