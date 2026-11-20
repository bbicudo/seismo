import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { fmtTime } from "../../lib/api";

export const dynamic = "force-dynamic";

const API = process.env.API_INTERNAL_URL || "http://api:8000";

async function load() {
  const [f, s, p] = await Promise.all([
    fetch(`${API}/v1/admin/flags`, { cache: "no-store" }).then((r) => r.json()),
    fetch(`${API}/v1/status`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)),
    fetch(`${API}/v1/admin/params`, { cache: "no-store" }).then((r) => r.json()),
  ]);
  return { ...f, status: s, params: p.params };
}

async function setParam(formData) {
  "use server";
  const key = String(formData.get("key") || "");
  const reset = formData.get("reset") === "1";
  const value = reset ? null : String(formData.get("value") ?? "");
  const r = await fetch(`${API}/v1/admin/params`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ key, value }), cache: "no-store",
  });
  revalidatePath("/admin");
  if (!r.ok) {
    const msg = (await r.json().catch(() => ({}))).detail || "valor recusado";
    redirect(`/admin?erro=${encodeURIComponent(`${key}: ${msg}`)}#parametros`);
  }
  redirect(`/admin?ok=${encodeURIComponent(key)}#parametros`);
}

function Param({ p, ok }) {
  const isNum = p.type === "int" || p.type === "float";
  const differs = p.applies === "coletor" && p.collector_value != null && String(p.collector_value) !== String(p.value);
  return (
    <form action={setParam} className="param" id={`p-${p.key}`}>
      <input type="hidden" name="key" value={p.key} />
      <div>
        <label htmlFor={`in-${p.key}`}><b>{p.label}</b></label>
        {p.help && <p className="muted" style={{ margin: "2px 0 0", fontSize: 14 }}>{p.help}</p>}
        <small className="muted">
          padrão: {String(p.default) || "vazio"}{isNum ? ` · de ${p.min} a ${p.max}` : ""} · vale para: {p.applies}
          {p.custom && p.updated_at ? ` · alterado` : ""}
          {differs ? ` · coletor ainda com ${p.collector_value} (aplica em até 30 s)` : ""}
          {ok === p.key ? " · salvo ✓" : ""}
        </small>
      </div>
      <div className="param-input">
        <input id={`in-${p.key}`} name="value" defaultValue={String(p.value)}
               type={isNum ? "number" : "text"} step={p.type === "float" ? "0.01" : "1"}
               min={isNum ? p.min : undefined} max={isNum ? p.max : undefined} />
        <button type="submit">Salvar</button>
        {p.custom && <button type="submit" name="reset" value="1" className="ghost">Padrão</button>}
      </div>
    </form>
  );
}

async function toggle(formData) {
  "use server";
  const key = String(formData.get("key") || "");
  const enabled = formData.get("enabled") === "1";
  await fetch(`${API}/v1/admin/flags`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ key, enabled }), cache: "no-store",
  });
  revalidatePath("/admin");
}

function Switch({ k, enabled, label, help, updated }) {
  return (
    <form action={toggle} className="flag">
      <input type="hidden" name="key" value={k} />
      <input type="hidden" name="enabled" value={enabled ? "0" : "1"} />
      <div>
        <b>{label}</b>
        <p className="muted" style={{ margin: "2px 0 0", fontSize: 14 }}>{help}</p>
        {updated && <small className="muted">alterado em {fmtTime(updated, "pt")}</small>}
      </div>
      <button type="submit" className={`switch ${enabled ? "on" : "off"}`} aria-pressed={enabled}
              aria-label={`${label}: ${enabled ? "ligado, clique para desligar" : "desligado, clique para ligar"}`}>
        <span>{enabled ? "ligado" : "desligado"}</span>
      </button>
    </form>
  );
}

export default async function Admin({ searchParams }) {
  const sp = await searchParams;
  const d = await load();
  const groups = [...new Set(d.params.map((p) => p.group))];
  const site = d.flags.filter((f) => f.group === "site");
  const coleta = d.flags.filter((f) => f.group === "coleta");
  const c = d.status?.collector;
  return (
    <>
      <section className="card">
        <h1>Feature flags</h1>
        <p className="lead">
          Liga e desliga cada parte do Seismo. Desligar uma parte do site esconde a seção, o item do menu e a rota da API.
          Desligar uma coleta para de fazer as requisições dela à TibiaData; ao religar, ela volta a rodar sozinha.
          As mudanças valem em até 10 segundos.
        </p>
        {c && (
          <p className="muted">
            Coletor {c.paused ? "pausado" : "coletando"} · última rodada {fmtTime(c.last_cycle_at, "pt")} ·
            {" "}{c.requests_today_utc}{c.request_cap ? ` de ${c.request_cap}` : ""} requisições hoje (UTC) · {c.errors_today_utc} erros
            {c.budget_left != null && ` · folga para leituras de casas e guilds: ${c.budget_left}`}
          </p>
        )}
      </section>

      <section className="card">
        <h2>Coletor de online</h2>
        <Switch k="collector_online" enabled={!d.collector_paused} label="Fotos de online a cada 5 minutos"
                help="Base de quase tudo: mapa de calor, saúde, personagens, Wrapped. Desligar pausa também as coletas diárias." />
      </section>

      <div className="grid2" style={{ alignItems: "start" }}>
        <section className="card">
          <h2>Partes do site</h2>
          <div className="flags">
            {site.map((f) => <Switch key={f.key} k={f.key} enabled={f.enabled} label={f.label} help={f.help} updated={f.updated_at} />)}
          </div>
        </section>
        <section className="card">
          <h2>Coletas diárias</h2>
          <div className="flags">
            {coleta.map((f) => <Switch key={f.key} k={f.key} enabled={f.enabled} label={f.label} help={f.help} updated={f.updated_at} />)}
          </div>
          <p className="muted" style={{ marginTop: 12 }}>
            Sempre ligados, por obrigação: opt-out, página de privacidade e página sobre.
          </p>
        </section>
      </div>

      <section className="card" id="parametros">
        <h1 style={{ fontSize: 26 }}>Parâmetros</h1>
        <p className="lead">
          Valores que ajustam o comportamento do Seismo. O site aplica em até 10 segundos e o coletor em até 30, sem reiniciar.
          Cada campo só aceita valores dentro do intervalo indicado; "Padrão" volta ao valor original.
        </p>
        {sp.erro && <p className="pill red" style={{ whiteSpace: "normal" }}>Não salvo: {sp.erro}</p>}
        {groups.map((g) => (
          <div key={g} style={{ marginTop: 18 }}>
            <h2>{g}</h2>
            <div className="flags">{d.params.filter((p) => p.group === g).map((p) => <Param key={p.key} p={p} ok={sp.ok} />)}</div>
          </div>
        ))}
      </section>
    </>
  );
}
