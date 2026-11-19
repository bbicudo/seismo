// Textos e utilidades do Wrapped (resumo do mês), em pt e en.
export const W = {
  pt: {
    title: "Wrapped",
    lead: "O resumo do mês de um personagem, de uma guild ou de um mundo, pronto para compartilhar.",
    world: "Mundo",
    character: "Personagem",
    guild: "Guild",
    month: "Mês",
    see: "Ver Wrapped",
    world_link: "Wrapped do mundo",
    world_hint: "Para o Wrapped do mundo, escolha o mundo e deixe o nome vazio.",
    partial: "mês em andamento: os números ainda vão mudar",
    hours: "horas online",
    days: "dias jogados",
    best_day: "no dia mais longo",
    levels: "levels no mês",
    top: "do mundo em tempo online",
    top_of: "top {p}%",
    fav_day: "dia favorito",
    weekdays: ["", "segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"],
    in_guild: "{rank} na {guild}",
    no_guild: "sem guild",
    empty: "Ainda não há dados deste personagem neste mês.",
    not_found: "Não encontramos esse personagem nesse mundo. Ele precisa ter sido visto online pelo Seismo (e não ter feito opt-out).",
    avg_online: "jogadores online em média",
    peak: "pico do mês",
    deaths: "mortes para criaturas",
    kills: "criaturas mortas",
    new_chars: "personagens novos",
    arrived: "chegaram por transfer",
    left: "saíram por transfer",
    world_levels: "levels ganhos no mundo",
    top_creatures: "Mais caçadas",
    top_killers: "Mais mataram jogadores",
    joins: "entradas",
    leaves: "saídas",
    active: "membros ativos",
    members: "membros",
    member_hours: "horas online somadas",
    top_levelers: "Quem mais upou",
    share: "Compartilhe o link: a imagem aparece sozinha no Discord, WhatsApp e redes.",
  },
  en: {
    title: "Wrapped",
    lead: "A month in review for a character, a guild or a world, ready to share.",
    world: "World",
    character: "Character",
    guild: "Guild",
    month: "Month",
    see: "See Wrapped",
    world_link: "World Wrapped",
    world_hint: "For the world Wrapped, pick the world and leave the name empty.",
    partial: "month in progress: numbers will still change",
    hours: "hours online",
    days: "days played",
    best_day: "on the longest day",
    levels: "levels this month",
    top: "of the world by time online",
    top_of: "top {p}%",
    fav_day: "favorite day",
    weekdays: ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    in_guild: "{rank} of {guild}",
    no_guild: "no guild",
    empty: "No data for this character this month yet.",
    not_found: "We could not find that character in that world. It must have been seen online by Seismo (and not opted out).",
    avg_online: "players online on average",
    peak: "monthly peak",
    deaths: "deaths to creatures",
    kills: "creatures killed",
    new_chars: "new characters",
    arrived: "arrived by transfer",
    left: "left by transfer",
    world_levels: "levels gained in the world",
    top_creatures: "Most hunted",
    top_killers: "Deadliest to players",
    joins: "joins",
    leaves: "departures",
    active: "active members",
    members: "members",
    member_hours: "combined hours online",
    top_levelers: "Top levelers",
    share: "Share the link: the image shows up on its own in Discord, WhatsApp and social apps.",
  },
};

export function wt(locale) {
  return W[locale] || W.pt;
}

export function monthLabel(month, locale) {
  const [y, m] = month.split("-").map(Number);
  return new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "pt-BR", { month: "long", year: "numeric", timeZone: "UTC" })
    .format(new Date(Date.UTC(y, m - 1, 15)));
}

export function validMonth(m) {
  return typeof m === "string" && /^\d{4}-(0[1-9]|1[0-2])$/.test(m) ? m : "";
}

export function hours(minutes) {
  return Math.round((minutes || 0) / 6) / 10;
}
