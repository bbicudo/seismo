import { ogCard, OG_SIZE } from "../../components/og-card";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = "image/png";
export const alt = "Seismo";

const API = process.env.API_INTERNAL_URL || "http://api:8000";

// Imagem de prévia padrão das páginas que não têm a própria (aparece ao compartilhar o link).
export default async function Image({ params }) {
  const { locale } = await params;
  const en = locale === "en";
  let worlds = [];
  try { worlds = await (await fetch(`${API}/v1/worlds`, { cache: "no-store" })).json(); } catch {}
  const nf = new Intl.NumberFormat(en ? "en-GB" : "pt-BR");
  const online = worlds.reduce((s, w) => s + (w.players_online || 0), 0);
  return ogCard({
    kicker: "SEISMO",
    title: en ? "Feel every world shake" : "Sinta o tremor de cada mundo",
    subtitle: en ? "Live Tibia statistics: worlds, heatmaps, hunts, raids, guilds and houses"
                 : "Estatísticas de Tibia ao vivo: mundos, mapas de calor, hunts, raids, guilds e casas",
    stats: worlds.length ? [[nf.format(online), en ? "players online" : "jogadores online"],
                            [nf.format(worlds.length), en ? "worlds" : "mundos"]] : [],
  });
}
