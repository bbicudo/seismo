import { notFound } from "next/navigation";
import YasirList from "../../../../components/yasir-list";
import data from "../../../../data/yasir.json";
import { fmtDate, fmtNum } from "../../../../lib/api";
import { getFlags, on } from "../../../../lib/flags";
import { dict, fmt } from "../../../../lib/i18n";
import { seo } from "../../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  return seo(locale, "/utils/yasir", { title: t.yasir_title, description: t.yasir_lead });
}

export const dynamic = "force-dynamic";

// Lista do Yasir cruzada com o TibiaWiki: o que dá para vender sem perder dinheiro e o que vale guardar.
export default async function Yasir({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  const f = await getFlags();
  if (!on(f, "page_utils") || !on(f, "util_yasir")) notFound();
  const n = (s) => data.items.filter((r) => r.status === s).length;
  return (
    <>
      <section className="card">
        <p className="crumbs"><a href={`/${locale}/utils`}>← {t.utils_title}</a></p>
        <h1>{t.yasir_title}</h1>
        <p className="lead">{t.yasir_lead}</p>
        <div className="stats">
          <div className="stat"><b className="down">{fmtNum(n("keep"), locale)}</b><span>{t.yasir_keep}</span></div>
          <div className="stat"><b>{fmtNum(n("task"), locale)}</b><span>{t.yasir_task}</span></div>
          <div className="stat"><b className="up">{fmtNum(n("sell"), locale)}</b><span>{t.yasir_sell}</span></div>
        </div>
      </section>
      <section className="card">
        <YasirList items={data.items} locale={locale} />
      </section>
      <p className="muted">{fmt(t.yasir_credit, { d: fmtDate(data.updated, locale) })}</p>
    </>
  );
}
