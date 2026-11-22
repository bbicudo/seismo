import { notFound } from "next/navigation";
import { getFlags, on } from "../../../lib/flags";
import { ht } from "../../../lib/hunts-i18n";
import { dict } from "../../../lib/i18n";
import { seo } from "../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  return seo(locale, "/utils", { title: t.utils_title, description: t.utils_lead });
}

export const dynamic = "force-dynamic";

// Ferramentas do dia a dia do jogo. Cada uma tem a sua flag; a área inteira some com page_utils desligada.
export default async function Utils({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  const f = await getFlags();
  if (!on(f, "page_utils")) notFound();
  const h = ht(locale);
  const tools = [
    on(f, "util_hunts") && { href: `/${locale}/utils/hunts`, title: h.title, text: h.card },
    on(f, "util_yasir") && { href: `/${locale}/utils/yasir`, title: t.yasir_title, text: t.yasir_card },
  ].filter(Boolean);
  return (
    <section className="card">
      <h1>{t.utils_title}</h1>
      <p className="lead">{t.utils_lead}</p>
      {tools.length === 0 ? <p className="muted">{t.utils_none}</p> : (
        <div className="util-grid">
          {tools.map((x) => (
            <a key={x.href} href={x.href} className="util-card"><b>{x.title} →</b><span>{x.text}</span></a>
          ))}
        </div>
      )}
      {on(f, "feedback_form") && <p className="muted util-fb"><a href={`/${locale}/feedback?from=/${locale}/utils`}>{t.fb_link}</a></p>}
    </section>
  );
}
