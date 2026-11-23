import { notFound } from "next/navigation";
import ElementIcon from "../../../../../components/element-icon";
import data from "../../../../../data/hunt-places.json";
import { fmtDate, fmtNum } from "../../../../../lib/api";
import { getFlags, on } from "../../../../../lib/flags";
import { ATTACK, ICON_CDN, advise } from "../../../../../lib/hunt-advice";
import { EL, VOCS, gold, ht } from "../../../../../lib/hunts-i18n";
import { dict, fmt } from "../../../../../lib/i18n";
import { seo } from "../../../../../lib/seo";

const BY_SLUG = new Map(data.places.map((p) => [p.slug, p]));
const sprite = (c) => (c?.img ? `${ICON_CDN}${c.img}&path-prefix=en` : null);
const wiki = (name) => `https://tibia.fandom.com/wiki/${encodeURIComponent(name.replace(/ /g, "_"))}`;
const bestText = (t, b) => fmt(b.avg > 100 ? t.attack_best : t.attack_flat, { e: EL[b.e], n: b.avg });

export async function generateMetadata({ params }) {
  const { locale, slug } = await params;
  const p = BY_SLUG.get(slug);
  const t = ht(locale);
  if (!p) return {};
  const adv = advise(p, data.creatures);
  const lv = VOCS.filter((v) => p.voc[v]?.lvl).map((v) => `${t.vocs[v]} ${p.voc[v].lvl}+`).join(", ");
  return seo(locale, `/utils/hunts/${slug}`, {
    title: `${p.name} · ${t.title}`,
    description: [p.city, lv, p.creatures.slice(0, 5).join(", "), adv.bestElement && bestText(t, adv.bestElement)].filter(Boolean).join(" · "),
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
          <span><a href={wiki(name)} target="_blank" rel="noopener noreferrer">{name.replace(/ \(Creature\)$/, "")}</a></span>
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

export default async function HuntPlace({ params }) {
  const { locale, slug } = await params;
  const f = await getFlags();
  if (!on(f, "page_utils") || !on(f, "util_hunts")) notFound();
  const p = BY_SLUG.get(slug);
  if (!p) notFound();
  const t = ht(locale);
  const adv = advise(p, data.creatures);
  const icons = data.icons;
  const vocs = VOCS.filter((v) => p.voc[v]);
  const hasExtra = vocs.some((v) => p.voc[v].extra);
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={`/${locale}/utils/hunts`}>← {t.back}</a></p>
        <h1>{p.name}</h1>
        <p className="lead">
          {[p.city,
            p.video && <a key="v" href={p.video} target="_blank" rel="noopener noreferrer">{t.video} ↗</a>,
            p.wiki_area && <a key="w" href={wiki(p.wiki_area)} target="_blank" rel="noopener noreferrer">{t.wiki} ↗</a>,
          ].filter(Boolean).flatMap((x, i) => (i ? [" · ", x] : [x]))}
        </p>
      </section>

      <section className="card">
        <h2>{t.tested_title}</h2>
        <p className="lead">{t.tested_lead}</p>
        <div className="tbl"><table className="compact cards">
          <thead><tr>
            <th>{t.vocation}</th><th className="n">{t.lvl}</th><th className="n">{t.exp}</th><th className="n">{t.loot}</th>
            {hasExtra && <th>{t.extra_any}</th>}
          </tr></thead>
          <tbody>
            {vocs.map((v) => {
              const x = p.voc[v];
              return (
                <tr key={v}>
                  <td className="place">{t.vocs[v]}</td>
                  <td className="n">{x.lvl ? `${x.lvl}+` : "–"}</td>
                  <td className={`n${x.exp == null ? " empty" : ""}`}>{gold(x.exp, locale)}</td>
                  <td className={`n${x.loot == null ? " empty" : x.loot < 0 ? " down" : ""}`}>{gold(x.loot, locale)}</td>
                  {hasExtra && <td className={x.extra ? "" : "empty"}>{x.extra || "–"}</td>}
                </tr>
              );
            })}
          </tbody>
        </table></div>
        <p className="muted" style={{ marginTop: 8 }}><a href="https://tibiapal.com/hunting" target="_blank" rel="noopener">{t.credit_pal}</a></p>
      </section>

      {p.creatures.length === 0 ? <section className="card"><p className="muted">{t.no_monsters}</p></section> : (
        <>
          <div className="grid-even">
            <section className="card">
              <h2>{t.attack_title}</h2>
              <p className="lead">{t.attack_lead}</p>
              {adv.bestElement && <p className="advice">{bestText(t, adv.bestElement)}</p>}
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
              <tbody>{p.creatures.map((n) => <Monster key={n} name={n} icons={icons} locale={locale} />)}</tbody>
            </table></div>
          </section>
        </>
      )}
      {on(f, "feedback_form") && (
        <p className="muted"><a href={`/${locale}/feedback?f=hunts&from=/${locale}/utils/hunts/${slug}`}>{dict(locale).fb_link}</a></p>
      )}
      <p className="muted">{fmt(t.credit, { d: fmtDate(data.updated, locale) })}</p>
    </>
  );
}
