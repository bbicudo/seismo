import { notFound } from "next/navigation";
import HuntAreaList from "../../../../components/hunt-area-list";
import data from "../../../../data/hunt-areas.json";
import { fmtDate } from "../../../../lib/api";
import { getFlags, on } from "../../../../lib/flags";
import { advise, minLevel } from "../../../../lib/hunt-advice";
import { ht } from "../../../../lib/hunts-i18n";
import { dict, fmt } from "../../../../lib/i18n";
import { seo } from "../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const t = ht(locale);
  return seo(locale, "/utils/hunts", { title: t.title, description: t.card });
}

export const dynamic = "force-dynamic";

// Lista enxuta para o navegador: só o que a tabela e os filtros usam (o detalhe fica na página de cada área).
const ROWS = data.areas.map((a) => {
  const adv = advise(a, data.creatures);
  return { slug: a.slug, name: a.name, city: a.city, lvl: a.lvl, min: minLevel(a), creatures: a.creatures,
    best: adv.bestElement?.e || null, protect: adv.protectTop.map((x) => x.e) };
}).sort((a, b) => a.name.localeCompare(b.name));
const CITIES = [...new Set(data.areas.map((a) => a.city).filter(Boolean))].sort();

export default async function HuntAreas({ params }) {
  const { locale } = await params;
  const t = ht(locale);
  const d = dict(locale);
  const f = await getFlags();
  if (!on(f, "page_utils") || !on(f, "util_hunts")) notFound();
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={`/${locale}/utils`}>← {d.utils_title}</a></p>
        <h1>{t.title}</h1>
        <p className="lead">{t.lead}</p>
      </section>
      <section className="card">
        <HuntAreaList rows={ROWS} cities={CITIES} icons={data.icons} locale={locale} />
      </section>
      {on(f, "feedback_form") && <p className="muted"><a href={`/${locale}/feedback?f=hunts&from=/${locale}/utils/hunts`}>{d.fb_link}</a></p>}
      <p className="muted">{fmt(t.credit, { d: fmtDate(data.updated, locale) })}</p>
    </>
  );
}
