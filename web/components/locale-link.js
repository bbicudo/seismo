"use client";

import { usePathname, useSearchParams } from "next/navigation";

// Troca só o idioma do endereço e mantém a página, os filtros e a âncora (ex.: /pt/utils/yasir → /en/utils/yasir).
export default function LocaleLink({ to, label }) {
  const path = usePathname() || "/";
  const sp = useSearchParams();
  const rest = path.replace(/^\/(pt|en)(?=\/|$)/, "");
  const qs = sp?.toString();
  const href = `/${to}${rest}${qs ? `?${qs}` : ""}`;
  return <a href={href} hrefLang={to} onClick={(e) => { if (window.location.hash) e.currentTarget.href = href + window.location.hash; }}>{label}</a>;
}
