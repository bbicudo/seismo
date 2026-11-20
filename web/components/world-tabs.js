"use client";
// Abas do mundo. Marca a aba da página atual (as páginas de guild, cidade e casa ficam sob Guilds e Casas)
// e rola a aba ativa para a vista no celular, onde as abas viram uma faixa que desliza para o lado.
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

export default function WorldTabs({ base, tabs, label, extra }) {
  const path = usePathname() || "";
  const rest = decodeURIComponent(path).slice(decodeURIComponent(base).length).split("/")[1] || "";
  const ref = useRef(null);
  useEffect(() => {
    ref.current?.querySelector('[aria-current="page"]')?.scrollIntoView({ block: "nearest", inline: "center" });
  }, [rest]);
  return (
    <nav className="tabs" aria-label={label} ref={ref}>
      {tabs.map((t) => {
        const active = t.match.includes(rest);
        return (
          <a key={t.href} href={t.href} aria-current={active ? "page" : undefined} className={active ? "on" : undefined}>
            {t.label}
          </a>
        );
      })}
      {extra && <a href={extra.href} className="tab-extra">{extra.label}</a>}
    </nav>
  );
}
