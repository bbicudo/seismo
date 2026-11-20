// Feature flags definidas na área administrativa. Sem resposta da API, tudo fica ligado.
const API = process.env.API_INTERNAL_URL || "http://api:8000";

export async function getFlags() {
  try {
    const r = await fetch(`${API}/v1/flags`, { cache: "no-store" });
    return r.ok ? await r.json() : {};
  } catch {
    return {};
  }
}

export function on(flags, key) {
  return flags[key] !== false;
}
