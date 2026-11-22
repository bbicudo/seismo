import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { fmtNum, fmtTime } from "../../lib/api";

export const dynamic = "force-dynamic";

const API = process.env.API_INTERNAL_URL || "http://api:8000";

async function load() {
  const [f, s, p, fb] = await Promise.all([
    fetch(`${API}/v1/admin/flags`, { cache: "no-store" }).then((r) => r.json()),
    fetch(`${API}/v1/admin/status`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)),
    fetch(`${API}/v1/admin/params`, { cache: "no-store" }).then((r) => r.json()),
    fetch(`${API}/v1/admin/feedback`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]);
  return { ...f, status: s, params: p.params, feedback: fb };
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
  const isBool = p.type === "bool";
  const show = (v) => (isBool ? (v ? "ligado" : "desligado") : String(v) || "vazio");
  const differs = p.applies === "coletor" && p.collector_value != null && String(p.collector_value) !== String(p.value);
  return (
    <form action={setParam} className="param" id={`p-${p.key}`}>
      <input type="hidden" name="key" value={p.key} />
      <div>
        <label htmlFor={`in-${p.key}`}><b>{p.label}</b></label>
        {p.help && <p className="muted" style={{ margin: "2px 0 0", fontSize: 14 }}>{p.help}</p>}
        <small className="muted">
          padrão: {show(p.default)}{isNum ? ` · de ${p.min} a ${p.max}` : ""} · vale para: {p.applies}
          {p.custom && p.updated_at ? ` · alterado` : ""}
          {differs ? ` · coletor ainda com ${p.collector_value} (aplica em até 30 s)` : ""}
          {ok === p.key ? " · salvo ✓" : ""}
        </small>
      </div>
      <div className="param-input">
        {isBool ? (
          <select id={`in-${p.key}`} name="value" defaultValue={p.value ? "true" : "false"}>
            <option value="true">ligado</option>
            <option value="false">desligado</option>
          </select>
        ) : (
          <input id={`in-${p.key}`} name="value" defaultValue={String(p.value)}
                 type={isNum ? "number" : "text"} step={p.type === "float" ? "0.01" : "1"}
                 min={isNum ? p.min : undefined} max={isNum ? p.max : undefined} />
        )}
        <button type="submit">Salvar</button>
        {p.custom && <button type="submit" name="reset" value="1" className="ghost">Padrão</button>}
      </div>
    </form>
  );
}

// Explicação curta de cada motivo de erro da TibiaData (o coletor já repete sozinho os temporários).
function explainError({ kind, reason }) {
  if (reason === "404") return "Não encontrado: guild que acabou, casa ou personagem que não existe mais. Esperado.";
  if (reason === "502" && kind === "character") return "A TibiaData responde 502 para personagem inexistente (nome errado no opt-out). Esperado.";
  if (reason === "429") return "Limite de ritmo da TibiaData: o coletor esperou e tentou de novo.";
  if (["500", "502", "503", "504"].includes(reason)) return "Falha temporária da TibiaData ou do tibia.com: o coletor tentou de novo.";
  if (/Timeout|Connect|Transport|Protocol|Read|Network/.test(reason)) return "Sem resposta a tempo ou conexão caiu: o coletor tentou de novo.";
  return "Resposta inesperada; se repetir muito, vale olhar o log do coletor.";
}

async function feedbackAction(formData) {
  "use server";
  const id = Number(formData.get("id"));
  const action = String(formData.get("action") || "");
  await fetch(`${API}/v1/admin/feedback/${id}`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action }), cache: "no-store",
  });
  revalidatePath("/admin");
  redirect("/admin#sugestoes");
}

const FEATURE_LABEL = { hunts: "Áreas de caça", yasir: "Vender ao Yasir", site: "Outra parte do site" };

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

      {d.status && (
        <section className="card">
          <h2>Status do coletor</h2>
          <div className="stats">
            <div className="stat"><b>{fmtNum(d.status.collector.requests_today_utc)}</b><span>requisições hoje (UTC){d.status.collector.request_cap ? ` de ${fmtNum(d.status.collector.request_cap)}` : ""}</span></div>
            <div className="stat"><b>{fmtNum(d.status.collector.errors_today_utc)}</b><span>erros hoje</span></div>
            <div className="stat"><b>{d.status.collector.last_cycle_seconds != null ? `${d.status.collector.last_cycle_seconds.toFixed(0)} s` : "–"}</b><span>última rodada ({d.status.collector.last_cycle_worlds || "–"} mundos)</span></div>
            <div className="stat"><b>{fmtNum(d.status.database.characters)}</b><span>personagens vistos</span></div>
            <div className="stat"><b>{(d.status.database.db_bytes / 1e6).toFixed(0)} MB</b><span>banco</span></div>
          </div>
          <div className="tbl" style={{ marginTop: 14 }}><table>
            <thead><tr><th>Coleta diária</th><th>Dia de jogo</th><th className="n">Itens</th><th className="n">Duração</th><th>Terminou</th></tr></thead>
            <tbody>
              {Object.entries(d.status.daily_jobs).map(([k, j]) => (
                <tr key={k}><td>{k}</td><td>{j.day || "aguardando"}</td><td className="n">{fmtNum(j.items)}</td>
                  <td className="n">{j.seconds ? `${Math.max(1, Math.round(j.seconds / 60))} min` : "–"}</td><td>{fmtTime(j.finished_at, "pt")}</td></tr>
              ))}
            </tbody>
          </table></div>
          {d.status.collector.errors_today_utc > 0 && (
            <>
              <h3 style={{ marginTop: 16 }}>Erros de hoje (UTC)</h3>
              {(d.status.errors_by || []).length === 0 ? (
                <p className="muted">O detalhamento começou a ser registrado agora; os erros anteriores a esta versão aparecem só no total.</p>
              ) : (
                <div className="tbl"><table>
                  <thead><tr><th>Consulta</th><th>Motivo</th><th className="n">Vezes</th><th>O que significa</th></tr></thead>
                  <tbody>
                    {d.status.errors_by.map((e) => (
                      <tr key={e.kind + e.reason}><td>{e.kind}</td><td>{e.reason}</td><td className="n">{fmtNum(e.n)}</td>
                        <td className="muted" style={{ whiteSpace: "normal" }}>{explainError(e)}</td></tr>
                    ))}
                  </tbody>
                </table></div>
              )}
            </>
          )}
          <p className="muted">
            Detalhes de guild lidos: {fmtNum(d.status.progress.guilds_read)} de {fmtNum(d.status.progress.guilds)} ·
            {" "}donos de casa lidos: {fmtNum(d.status.progress.houses_read)} de {fmtNum(d.status.progress.houses)} ·
            {" "}linhas de kill statistics: {fmtNum(d.status.progress.kill_rows)}
          </p>
        </section>
      )}

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

      {d.feedback && (
        <section className="card" id="sugestoes">
          <h2>Sugestões de correção {d.feedback.pending > 0 && <span className="pill red">{d.feedback.pending} novas</span>}</h2>
          <p className="muted">Enviadas pelo link "Encontrou um erro?". Sem nome, e-mail ou IP.</p>
          {d.feedback.items.length === 0 ? <p className="muted">Nenhuma sugestão ainda.</p> : (
            <div className="tbl"><table>
              <thead><tr><th>Quando</th><th>Onde</th><th>Sugestão</th><th></th></tr></thead>
              <tbody>
                {d.feedback.items.map((x) => (
                  <tr key={x.id} style={x.resolved ? { opacity: 0.55 } : undefined}>
                    <td>{fmtTime(x.created_at, "pt")}</td>
                    <td>{FEATURE_LABEL[x.feature] || x.feature}{x.page && <><br /><a href={x.page} className="muted">{x.page}</a></>}</td>
                    <td style={{ whiteSpace: "pre-wrap", minWidth: 280 }}>{x.message}</td>
                    <td>
                      <form action={feedbackAction} style={{ display: "flex", gap: 6 }}>
                        <input type="hidden" name="id" value={x.id} />
                        <button type="submit" name="action" value={x.resolved ? "reopen" : "resolve"} className="ghost">{x.resolved ? "Reabrir" : "Resolvida"}</button>
                        <button type="submit" name="action" value="delete" className="ghost">Apagar</button>
                      </form>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </section>
      )}

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
