// Recomendações de cada área de caça a partir dos monstros dela (dados do TibiaWiki).
// - Tipo de dano: média de quanto cada monstro apanha de cada elemento (cada monstro pesa igual; bosses fora).
// - Proteção: para cada monstro, a fatia de cada elemento no dano máximo que ele bate; a média das fatias
//   diz de onde vem o dano da área.

export const ATTACK = ["physical", "fire", "ice", "earth", "energy", "holy", "death"];
export const DAMAGE = [...ATTACK, "lifedrain", "manadrain", "drown"];
export const ICON_CDN = "https://static.wikia.nocookie.net/tibia/images/";
export const iconUrl = (path) => (path ? `${ICON_CDN}${path}&path-prefix=en` : null);

const avg = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;

export function advise(area, creatures) {
  const list = area.creatures.map((name) => ({ name, ...creatures[name] })).filter((c) => c.mods);
  const attack = ATTACK.map((e) => {
    const vals = list.map((c) => c.mods[e]).filter((v) => v != null);
    return vals.length ? { e, avg: Math.round(avg(vals)), min: Math.min(...vals), max: Math.max(...vals) } : null;
  }).filter(Boolean).sort((a, b) => b.avg - a.avg || b.min - a.min);

  const withDmg = list.filter((c) => c.dmg && Object.keys(c.dmg).length);
  const share = {};
  const top = {};
  for (const c of withDmg) {
    const total = Object.values(c.dmg).reduce((a, b) => a + b, 0) || 1;
    for (const [e, v] of Object.entries(c.dmg)) {
      share[e] = (share[e] || 0) + v / total;
      top[e] = Math.max(top[e] || 0, v);
    }
  }
  const protect = Object.entries(share)
    .map(([e, s]) => ({ e, pct: Math.round((100 * s) / withDmg.length), hit: top[e] }))
    .sort((a, b) => b.pct - a.pct);

  const elemental = attack.filter((x) => x.e !== "physical");
  return {
    attack,
    bestElement: elemental[0] || null,
    physical: attack.find((x) => x.e === "physical") || null,
    protect,
    // proteções que valem a pena: elementos com pelo menos 15% do dano da área (até 3), sem o físico se ele domina
    protectTop: protect.filter((x) => x.pct >= 15).slice(0, 3),
    unknownDamage: list.filter((c) => !c.dmg || !Object.keys(c.dmg).length).map((c) => c.name),
    analysed: list.length,
  };
}

export function minLevel(area) {
  const v = Object.values(area.lvl || {});
  return v.length ? Math.min(...v) : null;
}
