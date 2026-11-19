import { redirect } from "next/navigation";
import { IBM_Plex_Mono, IBM_Plex_Sans, Pixelify_Sans } from "next/font/google";
import { LOCALES, dict } from "../../lib/i18n";
import "../globals.css";

const display = Pixelify_Sans({ subsets: ["latin"], weight: ["500", "700"], variable: "--f-display" });
const body = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "600"], variable: "--f-body" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "600"], variable: "--f-mono" });

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
            <a href={`/${locale}`} className="brand"><b>Seismo</b><small>{t.tagline}</small></a>
            <span className="lab">{t.lab}</span>
            <nav className="main" aria-label="Seismo">
              <a href={`/${locale}`}>{t.nav_worlds}</a>
              <a href={`/${locale}/status`}>{t.nav_status}</a>
              <a href={`/${other}`} hrefLang={other}>{t.other_locale}</a>
            </nav>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="wrap">{t.footer}</footer>
      </body>
    </html>
  );
}
