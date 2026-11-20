// Metadados de SEO por página: título, descrição, canonical e o par em outro idioma (hreflang).
export function seo(locale, path, { title, description, noindex = false } = {}) {
  const languages = { "pt-BR": `/pt${path}`, en: `/en${path}`, "x-default": `/en${path}` };
  return {
    title,
    description,
    alternates: { canonical: `/${locale}${path}`, languages },
    openGraph: { title: title ? `${title} · Seismo` : "Seismo", description, url: `/${locale}${path}` },
    twitter: { card: "summary_large_image", title: title ? `${title} · Seismo` : "Seismo", description },
    ...(noindex ? { robots: { index: false, follow: true } } : {}),
  };
}

export const D = {
  world: { pt: (w) => `${w}: jogadores online agora, saúde do mundo, mapa de calor, raids, hunts, guilds e casas.`,
           en: (w) => `${w}: players online now, world health, activity heatmap, raids, hunts, guilds and houses.` },
  hunts: { pt: (w) => `Mapa de hunts de ${w}: as áreas de caça mais movimentadas do dia, a partir das kill statistics.`,
           en: (w) => `${w} hunt map: the busiest hunting areas of the day, from kill statistics.` },
  raids: { pt: (w) => `Raids detectadas em ${w}, próxima janela provável e termômetro de respawn.`,
           en: (w) => `Raids detected in ${w}, likely next window and respawn thermometer.` },
  guild: { pt: (g, w) => `${g} (${w}): membros, entradas e saídas, vocações e quando a guild joga.`,
           en: (g, w) => `${g} (${w}): members, joins and departures, vocations and when the guild plays.` },
  town: { pt: (t, w) => `Casas em ${t} (${w}): leilões abertos, lances e donos.`,
          en: (t, w) => `Houses in ${t} (${w}): open auctions, bids and owners.` },
  house: { pt: (h, w) => `${h} (${w}): situação, leilão e histórico de donos.`,
           en: (h, w) => `${h} (${w}): status, auction and owner history.` },
  wrappedWorld: { pt: (w) => `O mês de ${w} em números: online, mortes, levels ganhos e criaturas mais caçadas.`,
                  en: (w) => `${w}'s month in numbers: players online, deaths, levels gained and most hunted creatures.` },
  wrappedGuild: { pt: (g) => `O mês da guild ${g}: membros ativos, horas online, levels ganhos e quem mais upou.`,
                  en: (g) => `${g}'s month: active members, hours online, levels gained and top levelers.` },
  wrappedChar: { pt: (c) => `O mês de ${c} no Tibia: horas online, dias jogados e levels ganhos.`,
                 en: (c) => `${c}'s month in Tibia: hours online, days played and levels gained.` },
  character: { pt: (c) => `${c}: level, horas online por dia, levels por mês e guild.`,
               en: (c) => `${c}: level, hours online per day, levels per month and guild.` },
};
