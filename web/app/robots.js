// robots.txt: tudo liberado, menos a área administrativa e a API (JSON não precisa ir para os buscadores).
export const dynamic = "force-dynamic";

export default function robots() {
  const base = process.env.PUBLIC_URL || "http://localhost:3000";
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/admin", "/api/"] }],
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}
