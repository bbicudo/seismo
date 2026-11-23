"use client";

import { useMemo, useState } from "react";
import ElementIcon from "./element-icon";
import { VOCS, gold, ht } from "../lib/hunts-i18n";

const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
// começo de qualquer palavra ("cave" acha Hero Cave, não "Excavation")
const hit = (text, k) => {
  const n = norm(text);
  for (let i = 0; i < n.length; i++) if ((i === 0 || " '(-/".includes(n[i - 1])) && n.startsWith(k, i)) return true;
  return false;
};

// Lista de hunts do TibiaPal: os números (level, exp, loot, arma) são da vocação escolhida.
export default function HuntAreaList({ rows, cities, icons, locale = "pt" }) {
  const t = ht(locale);
  const [q, setQ] = useState("");
  const [city, setCity] = useState("");
  const [voc, setVoc] = useState("knight");
  const [lvl, setLvl] = useState("");
  const [sort, setSort] = useState("lvl");
  const ofVoc = useMemo(() => rows.filter((r) => r.voc[voc]), [rows, voc]);
  // levels que existem nas hunts da vocação (o TibiaPal usa levels mínimos como 8, 20, 100, 300...)
  const levels = useMemo(() => [...new Set(ofVoc.map((r) => r.voc[voc].lvl).filter(Boolean))].sort((a, b) => a - b), [ofVoc, voc]);
  const shown = useMemo(() => {
    const k = norm(q.trim());
    const my = levels.includes(Number(lvl)) ? Number(lvl) : 0;
    const key = { lvl: (r) => r.voc[voc].lvl ?? 0, exp: (r) => -(r.voc[voc].exp ?? -1e12), loot: (r) => -(r.voc[voc].loot ?? -1e12) }[sort];
    return ofVoc.filter((r) => (!k || hit(r.name, k) || r.creatures.some((c) => hit(c, k)))
      && (!city || r.city === city) && (!my || r.voc[voc].lvl === my))
      .sort((a, b) => key(a) - key(b) || (a.voc[voc].lvl ?? 0) - (b.voc[voc].lvl ?? 0) || a.name.localeCompare(b.name));
  }, [ofVoc, q, city, voc, lvl, sort, levels]);
  const extraHead = t.extra[voc];

  return (
    <>
      <div className="util-tools">
        <p className="seg" role="group" aria-label={t.vocation}>
          {VOCS.map((v) => (
            <a key={v} href="#" role="button" aria-current={voc === v ? "true" : undefined}
               onClick={(e) => { e.preventDefault(); setVoc(v); }}>{t.vocs[v]}</a>
          ))}
        </p>
        <label className="util-search">
          <span>{t.search}</span>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.placeholder} autoComplete="off" />
        </label>
        <form className="filters" onSubmit={(e) => e.preventDefault()}>
          <label>{t.city}
            <select value={city} onChange={(e) => setCity(e.target.value)}>
              <option value="">{t.all}</option>
              {cities.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label>{t.level}
            <select value={levels.includes(Number(lvl)) ? lvl : ""} onChange={(e) => setLvl(e.target.value)}>
              <option value="">{t.any}</option>
              {levels.map((v) => <option key={v} value={v}>{v}+</option>)}
            </select>
          </label>
          <label>{t.sort}
            <select value={sort} onChange={(e) => setSort(e.target.value)}>
              {Object.entries(t.sorts).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
        </form>
        <p className="muted util-hint">{shown.length === 1 ? t.count_one : t.count.replace("{n}", shown.length)}</p>
      </div>
      {shown.length === 0 ? <p className="muted">{t.none}</p> : (
        <div className="tbl"><table className="compact cards">
          <thead><tr>
            <th>{t.place}</th><th>{t.monsters}</th><th className="n">{t.lvl}</th><th className="n">{t.exp}</th><th className="n">{t.loot}</th>
            {extraHead && <th>{extraHead}</th>}<th>{t.protect}</th>
          </tr></thead>
          <tbody>
            {shown.map((r) => {
              const v = r.voc[voc];
              return (
                <tr key={r.slug}>
                  <td className="place"><a href={`/${locale}/utils/hunts/${r.slug}`}>{r.name}</a>{r.city && <small>{r.city}</small>}</td>
                  <td className={`wrap-cell${r.creatures.length ? "" : " empty"}`} data-label={t.monsters}>
                    {r.creatures.length ? `${r.creatures.slice(0, 4).join(", ")}${r.creatures.length > 4 ? ` +${r.creatures.length - 4}` : ""}` : "–"}
                  </td>
                  <td className="n" data-label={t.lvl}>{v.lvl ? `${v.lvl}+` : "–"}</td>
                  <td className={`n${v.exp == null ? " empty" : ""}`} data-label={t.exp}>{gold(v.exp, locale)}</td>
                  <td className={`n${v.loot == null ? " empty" : v.loot < 0 ? " down" : ""}`} data-label={t.loot}>{gold(v.loot, locale)}</td>
                  {extraHead && <td className={v.extra ? "" : "empty"} data-label={extraHead}>{v.extra || "–"}</td>}
                  <td className={r.protect.length ? "" : "empty"} data-label={t.protect}>
                    {r.protect.length ? <span className="el-list">{r.protect.map((e) => <ElementIcon key={e} e={e} icons={icons} />)}</span> : "–"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      )}
    </>
  );
}
