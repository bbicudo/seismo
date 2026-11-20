import { getParams } from "../lib/flags";

// robots.txt: liberado (menos /admin e /api) ou tudo bloqueado, conforme o parâmetro "Permitir buscadores".
export const dynamic = "force-dynamic";

export default async function robots() {
  const base = process.env.PUBLIC_URL || "http://localhost:3000";
  const p = await getParams();
  if (!p.seo_indexing) return { rules: [{ userAgent: "*", disallow: "/" }] };
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/admin", "/api/"] }],
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}
