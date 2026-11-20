import localFont from "next/font/local";
import "../globals.css";

const body = localFont({ src: "../fonts/ibm-plex-sans.woff2", weight: "100 700", variable: "--f-body", display: "swap" });
const mono = localFont({
  src: [
    { path: "../fonts/ibm-plex-mono-400.woff2", weight: "400" },
    { path: "../fonts/ibm-plex-mono-600.woff2", weight: "600" },
  ],
  variable: "--f-mono",
  display: "swap",
});
const display = localFont({ src: "../fonts/pixelify-sans.woff2", weight: "400 700", variable: "--f-display", display: "swap" });

export const metadata = { title: "Admin · Seismo", robots: { index: false, follow: false } };

export default function AdminLayout({ children }) {
  return (
    <html lang="pt-BR" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body>
        <header className="top">
          <div className="wrap">
            <a href="/admin" className="brand">
              <img src="/seismograph.gif" alt="" width="44" height="44" className="logo" />
              <b>Seismo</b><small>área administrativa</small>
            </a>
            <nav className="main"><a href="/pt">ver o site →</a></nav>
          </div>
        </header>
        <main className="wrap">{children}</main>
      </body>
    </html>
  );
}
