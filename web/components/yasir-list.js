"use client";

import { useMemo, useState } from "react";

const T = {
  pt: {
    search: "Buscar item", placeholder: "Nome do item, ex.: Blazing Bone",
    all: "Todos", keep: "Não venda", task: "Só sem Delivery Task", sell: "Pode vender",
    item: "Item", verdict: "O que fazer", pays: "Yasir paga (gp)", why: "Por quê",
    none: "Nenhum item com esse nome na lista do Yasir.", count: "{n} itens",
    wiki: "ver no TibiaWiki",
    tags: {
      imbuement: "imbuement", addon: "addon / outfit", quest: "quest", mount: "montaria", achievement: "conquista",
      craft: "usado para criar itens", use: "tem outro uso no jogo", task: "Delivery Task", warn: "o próprio Yasir avisa",
      rare: "caro: confira o market antes",
    },
    market: "mercado paga {m}", npc: "outro NPC paga {n} gp",
    task_why: "cai na Delivery Task semanal",
  },
  en: {
    search: "Find an item", placeholder: "Item name, e.g. Blazing Bone",
    all: "All", keep: "Don't sell", task: "Only without Delivery Task", sell: "Safe to sell",
    item: "Item", verdict: "What to do", pays: "Yasir pays (gp)", why: "Why",
    none: "No item with that name on Yasir's list.", count: "{n} items",
    wiki: "see on TibiaWiki",
    tags: {
      imbuement: "imbuement", addon: "addon / outfit", quest: "quest", mount: "mount", achievement: "achievement",
      craft: "used to make items", use: "has another in-game use", task: "Delivery Task", warn: "Yasir himself warns",
      rare: "pricey: check the market first",
    },
    market: "market pays {m}", npc: "another NPC pays {n} gp",
    task_why: "shows up in the weekly Delivery Task",
  },
};

const PILL = { keep: "pill red", task: "pill off", sell: "pill on" };
const FILTERS = ["all", "keep", "task", "sell"];

// sem acento e minúsculo, para a busca achar "Ghoul Snack" com "ghoul"
const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const wikiUrl = (name) => `https://tibia.fandom.com/wiki/${encodeURIComponent(name.replace(/\s*\(.*\)$/, "").replace(/ /g, "_"))}`;

export default function YasirList({ items, locale = "pt" }) {
  const t = T[locale] || T.pt;
  const [q, setQ] = useState("");
  const [f, setF] = useState("all");
  const nf = new Intl.NumberFormat(locale === "en" ? "en-GB" : "pt-BR");
  const rows = useMemo(() => {
    const k = norm(q.trim());
    return items.filter((r) => (f === "all" || r.status === f) && (!k || norm(r.name).includes(k)));
  }, [items, q, f]);

  const why = (r) => {
    const parts = (r.tags || []).filter((x) => x !== "market" && x !== "npc").map((x) => t.tags[x]);
    if (r.status === "task") parts.unshift(t.task_why);
    if (r.market) parts.push(t.market.replace("{m}", r.market.replace(/,/g, ".").replace(/ - /, "–") + " gp"));
    if (r.npc) parts.push(t.npc.replace("{n}", nf.format(r.npc)));
    return parts.join(" · ");
  };

  return (
    <>
      <div className="util-tools">
        <label className="util-search">
          <span>{t.search}</span>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.placeholder} autoComplete="off" />
        </label>
        <p className="seg" role="group">
          {FILTERS.map((k) => (
            <a key={k} href="#" role="button" aria-current={f === k ? "true" : undefined}
               onClick={(e) => { e.preventDefault(); setF(k); }}>{t[k]}</a>
          ))}
          <span className="muted">{t.count.replace("{n}", nf.format(rows.length))}</span>
        </p>
      </div>
      {rows.length === 0 ? <p className="muted">{t.none}</p> : (
        <div className="tbl"><table className="compact cards">
          <thead><tr><th>{t.item}</th><th>{t.verdict}</th><th className="n">{t.pays}</th><th>{t.why}</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.name}>
                <td className="place">{r.name}<small><a href={wikiUrl(r.name)} target="_blank" rel="noopener noreferrer">{t.wiki} ↗</a></small></td>
                <td data-label={t.verdict}><span className={PILL[r.status]}>{t[r.status]}</span></td>
                <td className="n" data-label={t.pays}>{nf.format(r.price)}</td>
                <td className={`wrap-cell${why(r) ? "" : " empty"}`} data-label={t.why}>{why(r) || "–"}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </>
  );
}
