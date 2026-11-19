import { NextResponse } from "next/server";

// "/" escolhe o idioma pelo navegador; rotas antigas do lab (/mundo/X) viram /pt/world/X.
export function middleware(req) {
  const { pathname } = req.nextUrl;
  if (pathname === "/") {
    const lang = (req.headers.get("accept-language") || "").toLowerCase();
    const locale = lang.startsWith("pt") || lang.includes(",pt") ? "pt" : lang ? "en" : "pt";
    return NextResponse.redirect(new URL(`/${locale}`, req.url));
  }
  const old = pathname.match(/^\/mundo\/(.+)$/);
  if (old) return NextResponse.redirect(new URL(`/pt/world/${old[1]}`, req.url), 308);
  return NextResponse.next();
}

export const config = { matcher: ["/", "/mundo/:path*"] };
