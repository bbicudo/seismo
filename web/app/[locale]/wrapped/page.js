import { getFlags, on } from "../../../lib/flags";
import { notFound, redirect } from "next/navigation";
import { api, enc } from "../../../lib/api";
import { wt } from "../../../lib/wrapped";

export const dynamic = "force-dynamic";
export const metadata = { title: "Wrapped" };

export default async function WrappedHome({ params }) {
  const { locale } = await params;
  const t = wt(locale);
  if (!on(await getFlags(), "page_wrapped")) notFound();
  const worlds = (await api("/v1/worlds")).map((w) => w.name).sort();

  async function go(formData) {
    "use server";
    const world = String(formData.get("world") || "");
    const name = String(formData.get("name") || "").replace(/\s+/g, " ").trim();
    const kind = String(formData.get("kind") || "character");
    if (!world) redirect(`/${locale}/wrapped`);
    if (!name) redirect(`/${locale}/wrapped/${enc(world)}`);
    redirect(kind === "guild" ? `/${locale}/wrapped/${enc(world)}/guild/${enc(name)}` : `/${locale}/wrapped/${enc(world)}/${enc(name)}`);
  }

  const input = { font: "inherit", padding: "6px 8px", border: "1px solid var(--line)", borderRadius: 4, background: "var(--paper)", color: "var(--ink)" };
  return (
    <section className="card wrapped">
      <div className="kicker">Seismo</div>
      <h1>{t.title}</h1>
      <p className="lead">{t.lead}</p>
      <form className="filters" action={go}>
        <label htmlFor="w-world">{t.world}
          <select id="w-world" name="world" required defaultValue="">
            <option value="" disabled>—</option>
            {worlds.map((w) => <option key={w} value={w}>{w}</option>)}
          </select>
        </label>
        <label htmlFor="w-kind">&nbsp;
          <select id="w-kind" name="kind" defaultValue="character">
            <option value="character">{t.character}</option>
            <option value="guild">{t.guild}</option>
          </select>
        </label>
        <label htmlFor="w-name">{t.character} / {t.guild}
          <input id="w-name" name="name" maxLength={40} style={input} />
        </label>
        <button type="submit">{t.see}</button>
      </form>
      <p className="muted">{t.world_hint}</p>
    </section>
  );
}
