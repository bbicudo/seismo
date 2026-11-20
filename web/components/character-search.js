"use client";

import { useEffect, useRef, useState } from "react";

const TXT = {
  pt: { label: "Buscar personagem", placeholder: "Nome do personagem", go: "Ver perfil", none: "Nenhum personagem encontrado." },
  en: { label: "Find a character", placeholder: "Character name", go: "View profile", none: "No character found." },
};

// Busca com sugestões enquanto digita (a partir de 3 letras). A API só devolve quem não fez opt-out.
export default function CharacterSearch({ locale = "pt" }) {
  const t = TXT[locale] || TXT.pt;
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [msg, setMsg] = useState("");
  const timer = useRef(null);

  useEffect(() => {
    clearTimeout(timer.current);
    if (q.trim().length < 3) { setItems([]); return; }
    timer.current = setTimeout(async () => {
      try {
        const r = await fetch(`/api/v1/characters?q=${encodeURIComponent(q.trim())}`);
        setItems(r.ok ? await r.json() : []);
      } catch { setItems([]); }
    }, 250);
    return () => clearTimeout(timer.current);
  }, [q]);

  function submit(e) {
    e.preventDefault();
    const name = q.trim();
    if (!name) return;
    const exact = items.find((i) => i.name.toLowerCase() === name.toLowerCase());
    if (!exact && items.length === 0) { setMsg(t.none); return; }
    window.location.href = `/${locale}/character/${encodeURIComponent(exact ? exact.name : items[0].name)}`;
  }

  return (
    <form className="filters charsearch" onSubmit={submit} role="search">
      <label htmlFor="char-q">{t.label}
        <input id="char-q" list="char-list" value={q} onChange={(e) => { setQ(e.target.value); setMsg(""); }}
               placeholder={t.placeholder} autoComplete="off" maxLength={30} />
      </label>
      <datalist id="char-list">
        {items.map((i) => <option key={i.name} value={i.name}>{`${i.level} · ${i.vocation} · ${i.world}`}</option>)}
      </datalist>
      <button type="submit">{t.go}</button>
      {msg && <p className="muted" style={{ flexBasis: "100%", margin: 0 }}>{msg}</p>}
    </form>
  );
}
