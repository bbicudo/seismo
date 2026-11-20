import { redirect } from "next/navigation";
import { fmtTime } from "../../../lib/api";
import { dict, fmt } from "../../../lib/i18n";

export const dynamic = "force-dynamic";
import { seo } from "../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const T = { pt: "Tirar meu personagem do Seismo", en: "Remove my character from Seismo" };
  const D = { pt: "Prove que é dono do personagem e tire ele do Seismo.", en: "Prove you own the character and remove it from Seismo." };
  const k = locale === "en" ? "en" : "pt";
  return seo(locale, "/opt-out", { title: T[k], description: D[k] });
}

const API = process.env.API_INTERNAL_URL || "http://api:8000";
const NAME_RE = /^[A-Za-z][A-Za-z' -]{1,28}[A-Za-z]$/;

const MSG_EN = {
  "código não encontrado no comentário do personagem": "the code was not found in the character comment",
  "aguarde 2 minutos entre verificações": "wait 2 minutes between checks",
  "personagem não encontrado (ou TibiaData indisponível); tente de novo em alguns minutos":
    "character not found (or TibiaData unavailable); try again in a few minutes",
};

async function post(path, name) {
  const r = await fetch(`${API}${path}`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name }), cache: "no-store",
  });
  return r.ok;
}

export default async function OptOut({ params, searchParams }) {
  const { locale } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const name = (sp.name || "").replace(/\s+/g, " ").trim();
  const valid = NAME_RE.test(name);
  const self = `/${locale}/opt-out`;

  async function start(formData) {
    "use server";
    const n = String(formData.get("name") || "").replace(/\s+/g, " ").trim();
    if (NAME_RE.test(n)) await post("/v1/optout/request", n);
    redirect(`${self}?name=${encodeURIComponent(n)}`);
  }

  async function verify(formData) {
    "use server";
    const n = String(formData.get("name") || "");
    if (NAME_RE.test(n)) await post("/v1/optout/verify", n);
    redirect(`${self}?name=${encodeURIComponent(n)}`);
  }

  let state = null;
  if (valid) {
    const r = await fetch(`${API}/v1/optout?name=${encodeURIComponent(name)}`, { cache: "no-store" });
    state = r.ok ? await r.json() : null;
  }
  const msg = state?.message ? (locale === "en" ? MSG_EN[state.message] || state.message : state.message) : "";
  const form = (
    <form className="filters" action={start}>
      <label htmlFor="optout-name">{t.optout_name}
        <input id="optout-name" name="name" required maxLength={30} defaultValue={name}
               style={{ font: "inherit", padding: "6px 8px", border: "1px solid var(--line)", borderRadius: 4, background: "var(--paper)", color: "var(--ink)" }} />
      </label>
      <button type="submit">{t.optout_start}</button>
    </form>
  );

  return (
    <section className="card">
      <h1>{t.optout_title}</h1>
      <p className="lead">{t.optout_lead}</p>
      {name && !valid && <p className="muted">{t.optout_invalid}</p>}
      {(!state || state.status === "none") && form}
      {state?.status === "expired" && (<><p className="muted">{t.optout_expired}</p>{form}</>)}
      {state && ["pending", "failed", "checking"].includes(state.status) && (
        <div style={{ display: "grid", gap: 10, maxWidth: "70ch" }}>
          <p><b>{state.name}</b></p>
          <p>{t.optout_step1}</p>
          <p><code style={{ fontSize: 20, padding: "4px 10px", userSelect: "all" }}>{state.code}</code></p>
          <p>{t.optout_step2}</p>
          <p>{t.optout_step3}</p>
          <p className="muted">{fmt(t.optout_expires, { date: fmtTime(state.expires_at, locale) })}</p>
          {state.status === "failed" && <p className="pill red" style={{ justifySelf: "start" }}>{fmt(t.optout_failed, { msg })}</p>}
          {state.status === "checking" ? (
            <>
              <p className="muted">{t.optout_checking}</p>
              <p><a href={`${self}?name=${encodeURIComponent(state.name)}`}>{t.optout_refresh}</a></p>
            </>
          ) : (
            <form action={verify} className="filters">
              <input type="hidden" name="name" value={state.name} />
              <button type="submit">{t.optout_verify}</button>
            </form>
          )}
          {msg && state.status !== "failed" && <p className="muted">{msg}</p>}
        </div>
      )}
      {state?.status === "verified" && (
        <>
          <p><span className="pill on">✓</span> {fmt(t.optout_done, { name: state.name })}</p>
          <p className="muted">{t.optout_kept}</p>
          <p><a href={self}>{t.optout_another}</a></p>
        </>
      )}
    </section>
  );
}
