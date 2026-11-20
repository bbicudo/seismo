import { revalidatePath } from "next/cache";
import { fmtTime } from "../../lib/api";

export const dynamic = "force-dynamic";

const API = process.env.API_INTERNAL_URL || "http://api:8000";

async function load() {
  const [f, s] = await Promise.all([
    fetch(`${API}/v1/admin/flags`, { cache: "no-store" }).then((r) => r.json()),
    fetch(`${API}/v1/status`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)),
  ]);
  return { ...f, status: s };
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

export default async function Admin() {
  const d = await load();
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
    </>
  );
}
