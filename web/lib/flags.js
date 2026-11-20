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

// Parâmetros públicos ajustados no /admin (SEO, contato). Sem resposta da API, valem os padrões.
const PARAM_DEFAULTS = {
  seo_indexing: true, seo_index_characters: false, seo_sitemap_guilds: true,
  seo_sitemap_towns: true, seo_sitemap_worlds_extra: true, public_contact: "",
};

export async function getParams() {
  try {
    const r = await fetch(`${API}/v1/params`, { cache: "no-store" });
    return r.ok ? { ...PARAM_DEFAULTS, ...(await r.json()) } : PARAM_DEFAULTS;
  } catch {
    return PARAM_DEFAULTS;
  }
}
