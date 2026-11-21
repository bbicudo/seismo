import { redirect } from "next/navigation";
import localFont from "next/font/local";
import { LOCALES, dict } from "../../lib/i18n";
import { getFlags, getParams, on } from "../../lib/flags";
import "../globals.css";

// Fontes dentro do projeto (licença SIL OFL): o build não depende de internet e
// o navegador do visitante não chama o Google.
const display = localFont({
  src: "../fonts/pixelify-sans.woff2", weight: "400 700", variable: "--f-display", display: "swap",
});
const body = localFont({
  src: "../fonts/ibm-plex-sans.woff2", weight: "100 700", variable: "--f-body", display: "swap",
});
const mono = localFont({
  src: [
    { path: "../fonts/ibm-plex-mono-400.woff2", weight: "400" },
    { path: "../fonts/ibm-plex-mono-600.woff2", weight: "600" },
  ],
  variable: "--f-mono",
  display: "swap",
});

export function generateStaticParams() {
  return LOCALES.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  const p = await getParams();
  return {
    metadataBase: new URL(process.env.PUBLIC_URL || "http://localhost:3000"),
    openGraph: { siteName: "Seismo", locale: locale === "pt" ? "pt_BR" : "en_GB", type: "website" },
    title: { default: `Seismo · ${t.tagline}`, template: "%s · Seismo" },
    description: t.overview_lead,
    robots: p.seo_indexing ? { index: true, follow: true } : { index: false, follow: false },
  };
}

// Tabelas com a classe "cards" viram cartões no celular: cada célula ganha o rótulo da sua coluna.
const CARD_LABELS = `document.querySelectorAll("table.cards").forEach(function(t){var h=[].map.call(t.querySelectorAll("thead th"),function(th){return th.textContent.trim()});t.querySelectorAll("tbody tr").forEach(function(r){var i=0;[].forEach.call(r.cells,function(c){if(!c.hasAttribute("data-label"))c.setAttribute("data-label",h[i]||"");if(c.textContent.trim()==="–")c.classList.add("empty");i+=c.colSpan||1})})})`;

export default async function LocaleLayout({ children, params }) {
  const { locale } = await params;
  if (!LOCALES.includes(locale)) redirect("/pt");
  const t = dict(locale);
  const f = await getFlags();
  const other = locale === "pt" ? "en" : "pt";
  return (
    <html lang={locale === "pt" ? "pt-BR" : "en"} className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body>
        <header className="top">
          <div className="wrap">
            <a href={`/${locale}`} className="brand">
              <img src="/seismograph.gif" alt="" width="44" height="44" className="logo" />
              <b>Seismo</b><small>{t.tagline}</small>
            </a>
            <span className="lab">{t.lab}</span>
            <nav className="main" aria-label="Seismo">
              <a href={`/${locale}`}>{t.nav_worlds}</a>
              {on(f, "page_events") && <a href={`/${locale}/events`}>{t.nav_events}</a>}
              {on(f, "page_wrapped") && <a href={`/${locale}/wrapped`}>Wrapped</a>}
              {on(f, "page_status") && <a href={`/${locale}/status`}>{t.nav_status}</a>}
              <a href={`/${other}`} hrefLang={other}>{t.other_locale}</a>
            </nav>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="wrap">
          <nav aria-label="Seismo" style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 6 }}>
            <a href={`/${locale}/about`}>{t.nav_about}</a>
            <a href={`/${locale}/privacy`}>{t.nav_privacy}</a>
            <a href={`/${locale}/opt-out`}>{t.nav_optout}</a>
          </nav>
          {t.footer}
        </footer>
        <script dangerouslySetInnerHTML={{ __html: CARD_LABELS }} />
      </body>
    </html>
  );
}
