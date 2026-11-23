"use client";

import { useMemo, useState } from "react";
import ElementIcon from "./element-icon";
import { ATTACK } from "../lib/hunt-advice";
import { EL, ht } from "../lib/hunts-i18n";

const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
// começo de qualquer palavra ("cave" acha Hero Cave, não "Excavation")
const hit = (text, k) => {
  const n = norm(text);
  for (let i = 0; i < n.length; i++) if ((i === 0 || " '(-".includes(n[i - 1])) && n.startsWith(k, i)) return true;
  return false;
};

export default function HuntAreaList({ rows, cities, icons, locale = "pt" }) {
  const t = ht(locale);
  const [q, setQ] = useState("");
  const [city, setCity] = useState("");
  const [el, setEl] = useState("");
  const [voc, setVoc] = useState("");
  const [lvl, setLvl] = useState("");
  // levels que existem nas hunts (da vocação escolhida, ou de todas)
  const levels = useMemo(() => [...new Set(rows.flatMap((r) => (voc ? [r.lvl[voc]] : Object.values(r.lvl))).filter(Boolean))]
    .sort((a, b) => a - b), [rows, voc]);
  const shown = useMemo(() => {
    const k = norm(q.trim());
    // level exato: as hunts do wiki usam levels redondos (100, 150, 200, 300, 600...), escolhidos numa lista;
    // ao trocar de vocação, um level que não existe nela deixa de filtrar
    const my = levels.includes(Number(lvl)) ? Number(lvl) : 0;
    const near = (r) => (voc ? [r.lvl[voc]] : Object.values(r.lvl)).includes(my);
    return rows.filter((r) => (!k || hit(r.name, k) || r.creatures.some((c) => hit(c, k)))
      && (!city || r.city === city) && (!el || r.best === el)
      && (!my || near(r)));
  }, [rows, q, city, el, voc, lvl, levels]);

  return (
    <>
      <div className="util-tools">
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
          <label>{t.element}
            <select value={el} onChange={(e) => setEl(e.target.value)}>
              <option value="">{t.any}</option>
              {ATTACK.filter((e) => e !== "physical").map((e) => <option key={e} value={e}>{EL[e]}</option>)}
            </select>
          </label>
          <label>{t.vocation}
            <select value={voc} onChange={(e) => setVoc(e.target.value)}>
              <option value="">{t.any}</option>
              {Object.entries(t.voc).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label>{t.level}
            <select value={levels.includes(Number(lvl)) ? lvl : ""} onChange={(e) => setLvl(e.target.value)}>
              <option value="">{t.any}</option>
              {levels.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
        </form>
        <p className="muted util-hint">{shown.length === 1 ? t.count_one : t.count.replace("{n}", shown.length)}</p>
      </div>
      {shown.length === 0 ? <p className="muted">{t.none}</p> : (
        <div className="tbl"><table className="compact cards">
          <thead><tr><th>{t.area}</th><th>{t.monsters}</th><th>{t.best}</th><th>{t.protect}</th><th className="n">{t.lvl}</th></tr></thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.slug}>
                <td className="place"><a href={`/${locale}/utils/hunts/${r.slug}`}>{r.name}</a>{r.city && <small>{r.city}</small>}</td>
                <td className="wrap-cell" data-label={t.monsters}>{r.creatures.slice(0, 5).join(", ")}{r.creatures.length > 5 ? ` +${r.creatures.length - 5}` : ""}</td>
                <td data-label={t.best} className={r.best ? "" : "empty"}>{r.best ? <ElementIcon e={r.best} icons={icons} /> : "–"}</td>
                <td data-label={t.protect} className={r.protect.length ? "" : "empty"}>
                  {r.protect.length ? <span className="el-list">{r.protect.map((e) => <ElementIcon key={e} e={e} icons={icons} />)}</span> : "–"}
                </td>
                <td className={`n${r.min ? "" : " empty"}`} data-label={t.lvl}>{r.min ?? "–"}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </>
  );
}
