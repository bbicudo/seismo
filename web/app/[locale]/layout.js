import { redirect } from "next/navigation";
import localFont from "next/font/local";
import { LOCALES, dict } from "../../lib/i18n";
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
  return {
    title: { default: `Seismo · ${t.tagline}`, template: "%s · Seismo" },
    description: t.overview_lead,
    robots: { index: false, follow: false },
  };
}

export default async function LocaleLayout({ children, params }) {
  const { locale } = await params;
  if (!LOCALES.includes(locale)) redirect("/pt");
  const t = dict(locale);
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
              <a href={`/${locale}/events`}>{t.nav_events}</a>
              <a href={`/${locale}/wrapped`}>Wrapped</a>
              <a href={`/${locale}/status`}>{t.nav_status}</a>
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
      </body>
    </html>
  );
}
