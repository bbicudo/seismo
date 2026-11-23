// Textos do utilitário de áreas de caça. Os elementos ficam com o nome do jogo (energy, earth...) nos dois idiomas.
export const EL = {
  physical: "Physical", fire: "Fire", ice: "Ice", earth: "Earth", energy: "Energy", holy: "Holy", death: "Death",
  lifedrain: "Life drain", manadrain: "Mana drain", drown: "Drown",
};

export const VOCS = ["knight", "paladin", "monk", "sorcerer", "druid", "teamhunt"];

// 1500000 -> "1,5kk", 45000 -> "45k" (como os jogadores e o TibiaPal escrevem)
export function gold(n, locale) {
  if (n == null) return "–";
  const nf = new Intl.NumberFormat(locale === "en" ? "en-GB" : "pt-BR", { maximumFractionDigits: 2 });
  const a = Math.abs(n);
  const s = a >= 1e6 ? `${nf.format(a / 1e6)}kk` : a >= 1e3 ? `${nf.format(a / 1e3)}k` : nf.format(a);
  return n < 0 ? `−${s}` : s;
}

const PT = {
  title: "Áreas de caça",
  card: "Hunts testadas pelo TibiaPal, por vocação e level, com exp e loot por hora, monstros, elemento e proteções.",
  lead: "Hunts testadas pelo TibiaPal para cada vocação, com os monstros do TibiaWiki: escolha a hunt e veja exp, loot, elemento e proteções.",
  search: "Buscar hunt ou monstro", placeholder: "Ex.: Dragons ou Hero Cave",
  city: "Cidade", all: "todas", vocation: "Vocação", level: "Level", sort: "Ordenar por",
  sorts: { lvl: "level", exp: "exp por hora", loot: "loot por hora" },
  vocs: { knight: "Knight", paladin: "Paladin", monk: "Monk", sorcerer: "Sorcerer", druid: "Druid", teamhunt: "Team hunt" },
  extra: { knight: "Tipo de arma", paladin: "Munição / barrage", monk: "Tipo de arma", sorcerer: "Mastery", druid: "Estilo", teamhunt: "" },
  extra_any: "Arma / munição / estilo",
  any: "qualquer",
  count: "{n} hunts", count_one: "1 hunt", none: "Nenhuma hunt com esses filtros.",
  place: "Hunt", monsters: "Monstros", protect: "Proteção", lvl: "Level", exp: "Exp/h", loot: "Loot/h",
  back: "Áreas de caça",
  tested_title: "Testado pelo TibiaPal",
  tested_lead: "Level mínimo, exp crua e loot por hora de cada vocação, nos testes do TibiaPal. Loot usa preços de mercado de servidores antigos.",
  video: "vídeo do teste", wiki: "área no TibiaWiki",
  attack_title: "Tipo de dano recomendado",
  attack_lead: "Quanto os monstros apanham de cada elemento, em média (100% = dano normal).",
  attack_best: "Use {e}: os monstros apanham {n}% em média.",
  attack_flat: "Nenhum elemento passa de 100% aqui. O que menos perde é {e} ({n}%).",
  attack_physical: "Dano físico: {n}% em média.",
  attack_range: "de {min}% a {max}%",
  protect_title: "Proteções recomendadas",
  protect_lead: "De onde vem o dano que os monstros batem, pela parte de cada elemento no dano máximo de cada um.",
  protect_best: "Proteja-se de {list}.",
  protect_none: "O wiki ainda não tem o dano destes monstros.",
  protect_hit: "maior golpe: {n}",
  unknown: "Sem dano conhecido no wiki: {list}.",
  no_monsters: "Não achamos os monstros desta hunt no TibiaWiki, então não há recomendação de elemento e proteção.",
  monsters_title: "Monstros",
  monster: "Monstro", hp: "HP", xp: "Exp", hits: "Bate",
  legend: "Na tabela, verde = apanha mais que o normal (bom para você); vermelho = apanha menos.",
  credit_pal: "Hunts, levels, exp, loot, arma e vídeos: TibiaPal (tibiapal.com), por Kusnier, usados com autorização.",
  credit: "Monstros, fraquezas e dano: TibiaWiki (tibia.fandom.com), licença CC BY-SA. Dados de {d}; imagens carregadas direto do TibiaWiki. Elemento e proteções são uma estimativa a partir do wiki.",
};

const EN = {
  title: "Hunting areas",
  card: "Hunts tested by TibiaPal, by vocation and level, with exp and loot per hour, monsters, element and protections.",
  lead: "Hunts tested by TibiaPal for each vocation, with monsters from TibiaWiki: pick a hunt and see exp, loot, element and protections.",
  search: "Find a hunt or monster", placeholder: "E.g. Dragons or Hero Cave",
  city: "Town", all: "all", vocation: "Vocation", level: "Level", sort: "Sort by",
  sorts: { lvl: "level", exp: "exp per hour", loot: "loot per hour" },
  vocs: { knight: "Knight", paladin: "Paladin", monk: "Monk", sorcerer: "Sorcerer", druid: "Druid", teamhunt: "Team hunt" },
  extra: { knight: "Weapon type", paladin: "Ammo / barrage", monk: "Weapon type", sorcerer: "Mastery", druid: "Playstyle", teamhunt: "" },
  extra_any: "Weapon / ammo / style",
  any: "any",
  count: "{n} hunts", count_one: "1 hunt", none: "No hunt matches these filters.",
  place: "Hunt", monsters: "Monsters", protect: "Protection", lvl: "Level", exp: "Exp/h", loot: "Loot/h",
  back: "Hunting areas",
  tested_title: "Tested by TibiaPal",
  tested_lead: "Minimum level, raw exp and loot per hour for each vocation, from TibiaPal's tests. Loot uses market prices from established worlds.",
  video: "test video", wiki: "area on TibiaWiki",
  attack_title: "Recommended damage type",
  attack_lead: "How much damage the monsters take from each element, on average (100% = normal damage).",
  attack_best: "Use {e}: the monsters take {n}% on average.",
  attack_flat: "No element goes above 100% here. The one that loses least is {e} ({n}%).",
  attack_physical: "Physical damage: {n}% on average.",
  attack_range: "from {min}% to {max}%",
  protect_title: "Recommended protections",
  protect_lead: "Where the monsters' damage comes from, by each element's share of each monster's maximum damage.",
  protect_best: "Protect against {list}.",
  protect_none: "TibiaWiki does not have these monsters' damage yet.",
  protect_hit: "biggest hit: {n}",
  unknown: "No known damage on TibiaWiki: {list}.",
  no_monsters: "We could not find this hunt's monsters on TibiaWiki, so there is no element or protection advice.",
  monsters_title: "Monsters",
  monster: "Monster", hp: "HP", xp: "Exp", hits: "Hits with",
  legend: "In the table, green = takes more than normal (good for you); red = takes less.",
  credit_pal: "Hunts, levels, exp, loot, weapons and videos: TibiaPal (tibiapal.com), by Kusnier, used with permission.",
  credit: "Monsters, weaknesses and damage: TibiaWiki (tibia.fandom.com), CC BY-SA license. Data from {d}; images load straight from TibiaWiki. Element and protections are an estimate from the wiki.",
};

export function ht(locale) {
  return locale === "en" ? EN : PT;
}
