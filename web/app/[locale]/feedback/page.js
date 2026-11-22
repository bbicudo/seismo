import { createHash } from "node:crypto";
import { headers } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { getFlags, on } from "../../../lib/flags";
import { dict } from "../../../lib/i18n";
import { seo } from "../../../lib/seo";

const API = process.env.API_INTERNAL_URL || "http://api:8000";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const t = dict(locale);
  return seo(locale, "/feedback", { title: t.fb_title, description: t.fb_lead, noindex: true });
}

export const dynamic = "force-dynamic";

// Envio pelo servidor do site: a rota da API fica fechada para fora. O endereço do visitante vira um hash do dia
// (só para limitar envios por hora) e não é guardado.
async function send(formData) {
  "use server";
  const locale = formData.get("locale") === "en" ? "en" : "pt";
  const back = (q) => redirect(`/${locale}/feedback?${new URLSearchParams(q)}`);
  if (formData.get("website")) back({ ok: "1" }); // campo invisível: robô
  const h = await headers();
  const ip = (h.get("x-forwarded-for") || "").split(",")[0].trim() || h.get("x-real-ip") || "desconhecido";
  const client = createHash("sha256").update(`${ip}|${new Date().toISOString().slice(0, 10)}`).digest("hex").slice(0, 32);
  const body = {
    feature: String(formData.get("feature") || ""), message: String(formData.get("message") || "").trim(),
    page: String(formData.get("page") || "") || null, locale, client,
  };
  if (body.message.length < 10) back({ f: body.feature, from: body.page || "", err: "short" });
  let r;
  try {
    r = await fetch(`${API}/v1/admin/feedback`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), cache: "no-store",
    });
  } catch {
    back({ f: body.feature, from: body.page || "", err: "fail" });
  }
  if (r.status === 429) back({ f: body.feature, err: "many" });
  if (!r.ok) back({ f: body.feature, from: body.page || "", err: "fail" });
  back({ ok: "1" });
}

export default async function Feedback({ params, searchParams }) {
  const { locale } = await params;
  const sp = await searchParams;
  const t = dict(locale);
  const f = await getFlags();
  if (!on(f, "feedback_form")) notFound();
  const options = [
    on(f, "page_utils") && on(f, "util_hunts") && ["hunts", t.fb_hunts],
    on(f, "page_utils") && on(f, "util_yasir") && ["yasir", t.fb_yasir],
    ["site", t.fb_site],
  ].filter(Boolean);
  const pre = options.some(([k]) => k === sp.f) ? sp.f : "";
  const from = typeof sp.from === "string" && sp.from.startsWith("/") ? sp.from.slice(0, 300) : "";
  if (sp.ok) {
    return (
      <section className="card">
        <h1>{t.fb_title}</h1>
        <p className="lead">{t.fb_thanks}</p>
        <p><a href={`/${locale}`}>← {t.back_home}</a></p>
      </section>
    );
  }
  return (
    <section className="card">
      <h1>{t.fb_title}</h1>
      <p className="lead">{t.fb_lead}</p>
      {sp.err && <p className="pill red" style={{ whiteSpace: "normal" }}>{t[`fb_err_${sp.err}`] || t.fb_err_fail}</p>}
      <form action={send} className="fb-form">
        <input type="hidden" name="locale" value={locale} />
        <input type="hidden" name="page" value={from} />
        <label className="fb-hp" aria-hidden="true">Website<input name="website" tabIndex={-1} autoComplete="off" /></label>
        <label>{t.fb_where}
          <select name="feature" defaultValue={pre} required>
            <option value="" disabled>{t.fb_choose}</option>
            {options.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </label>
        <label>{t.fb_what}
          <textarea name="message" rows={6} minLength={10} maxLength={2000} required placeholder={t.fb_placeholder} />
        </label>
        {from && <p className="muted">{t.fb_page} <code>{from}</code></p>}
        <p className="muted">{t.fb_privacy}</p>
        <button type="submit">{t.fb_send}</button>
      </form>
    </section>
  );
}
