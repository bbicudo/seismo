"""Gera web/data/hunt-places.json: locais de caça testados pelo TibiaPal cruzados com os monstros do TibiaWiki.

Uso: python tools/build_hunt_places.py  (depois de tools/build_hunt_areas.py, que gera as áreas do wiki)

- TibiaPal (tibiapal.com/hunting, por Kusnier, usado com autorização e crédito): para cada vocação, level mínimo,
  exp crua e loot por hora, arma/munição/estilo recomendado e o vídeo do teste. Uma consulta à página.
- TibiaWiki (CC BY-SA): os monstros de cada local, achados pelo nome no plural ("Swamp Trolls" -> Swamp Troll) ou,
  se o local cita uma área do wiki e nenhum monstro, pelos monstros dessa área. Fraquezas e dano de cada monstro.
"""
import html
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_hunt_areas as wiki  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/data/hunt-places.json"
AREAS = ROOT / "web/data/hunt-areas.json"
TIBIAPAL = "https://tibiapal.com/hunting"
VOCS = ["knight", "paladin", "monk", "sorcerer", "druid", "teamhunt"]
# abreviações que o TibiaPal usa nos nomes dos locais
CITY_ALIAS = {"lb": "Liberty Bay", "rosha": "Roshamuul", "ph": "Port Hope", "ab": "Ab'Dendriel", "yala": "Yalahar",
              "kaz": "Kazordoon", "ank": "Ankrahmun", "dara": "Darashia"}


def relevant(names: list[str], cdata: dict) -> list[str]:
    """tira bichos de passagem (borboleta, pinguim): menos de 5% da exp do monstro que mais dá exp no local."""
    top = max((cdata[n].get("exp") or 0 for n in names), default=0)
    return [n for n in names if not top or (cdata[n].get("exp") or 0) >= 0.05 * top]


# abreviações do TibiaPal escritas por extenso no nome do local
NAME_ALIAS = [
    (r"\bLB\b", "Liberty Bay"), (r"\bPH\b", "Port Hope"), (r"\bPOI\b", "Pits of Inferno"),
    (r"\bMoSL\b|\bMOSL\b", "Mother of Scarabs Lair"), (r"\bRosha\b", "Roshamuul"), (r"\bYala\b", "Yalahar"),
    (r"\bWOTE\b|\bWote\b", "Wrath of the Emperor"), (r"\bINQ\b", "Inquisition"), (r"\bDT\b", "Dark Torturer"),
    (r"\bFeru\b", "Ferumbras' Ascension"), (r"\(SD\)", "(Sudden Death)"), (r"\bseal\b", "Seal"),
    (r"\bStage(\d)", r"Stage \1"), (r"\bRosh\b", "Roshamuul"), (r"Terrosleep", "Terrorsleep"),
    (r"\bEdron South Were\b", "Edron South Werecreatures"), (r"\bShockheads\b", "Shock Heads"),
]


def expand(name: str) -> str:
    for pat, rep in NAME_ALIAS:
        name = re.sub(pat, rep, name)
    return re.sub(r"\s+", " ", name).strip()


def same_place(name: str) -> str:
    """chave para juntar o mesmo local escrito de jeitos diferentes nas tabelas de cada vocação
    (ordem das palavras, plural e "'s" não contam: "Falcon's Eagle" = "Falcons Eagle")."""
    words = re.findall(r"[a-z0-9']+|-\d+", name.lower().replace("'s", ""))
    return " ".join(sorted(singular(w) for w in words))


def money(s: str) -> int | None:
    """'1.5kk' -> 1500000, '45k' -> 45000, '-100k' -> -100000, '-' -> None."""
    s = s.strip().lower().replace(",", ".")
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(kk|k)?", s)
    if not m:
        return None
    return int(round(float(m.group(1)) * {"kk": 1_000_000, "k": 1_000, None: 1}[m.group(2)]))


def tibiapal() -> dict[str, dict]:
    req = urllib.request.Request(TIBIAPAL, headers=wiki.UA)
    page = urllib.request.urlopen(req, timeout=40).read().decode("utf8")
    starts = [m.start() for m in re.finditer(r"<table", page)]
    places: dict[str, dict] = {}
    for voc, p in zip(VOCS, starts):
        table = page[p:page.find("</table>", p)]
        for row in re.findall(r"<tr.*?</tr>", table, re.S)[1:]:
            tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            if len(tds) < 4:
                continue
            txt = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in tds]
            video = re.search(r'href="(https://(?:youtu\.be|www\.youtube\.com)/[^"]+)"', tds[1])
            name = expand(txt[1])
            entry = {"lvl": wiki.num(txt[0]), "exp": money(txt[2]), "loot": money(txt[3])}
            extra = txt[4] if len(txt) > 4 and txt[4] not in ("", "-", "N/A") else None
            if extra:
                entry["extra"] = extra
            place = places.setdefault(same_place(name), {"name": name, "voc": {}})
            place["voc"].setdefault(voc, entry)  # mesmo local duas vezes na mesma vocação: fica a primeira linha
            if video and "video" not in place:
                place["video"] = video.group(1)
    return places


def creature_index():
    """(nome em minúsculas no singular e no plural -> criatura, dados de cada criatura) para todo o wiki.
    Com SEISMO_WIKI_CACHE apontando para um arquivo, guarda o resultado e reaproveita nas próximas rodadas."""
    cache = os.environ.get("SEISMO_WIKI_CACHE")
    if cache and Path(cache).exists():
        index, data = json.loads(Path(cache).read_text(encoding="utf8"))
        return index, data
    index, data = _creature_index()
    if cache:
        Path(cache).write_text(json.dumps([index, data], ensure_ascii=False), encoding="utf8")
    return index, data


def _creature_index():
    titles, cont = [], {}
    while True:
        d = wiki.get({"action": "query", "list": "categorymembers", "cmtitle": "Category:Creatures",
                      "cmlimit": 500, **cont})
        titles += [m["title"] for m in d["query"]["categorymembers"] if m["ns"] == 0]
        if "continue" not in d:
            break
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}
        time.sleep(0.5)
    texts = wiki.pages(titles)
    index, data = {}, {}
    for title, txt in texts.items():
        c = wiki.parse_creature(txt)
        if not c:
            continue
        data[title] = c
        name = re.sub(r"\s*\(Creature\)$", "", title)
        index[name.lower()] = title
        plural = wiki.clean(wiki.field(txt, "plural"))
        if plural and plural != "--":
            index[plural.lower()] = title
    return index, data


def find_creatures(place: str, index: dict[str, str]) -> list[str]:
    text = re.sub(r"[()]|-\d+|\+\d+", " ", place).lower()
    found = []
    for key in sorted(index, key=len, reverse=True):  # o nome mais longo primeiro ("ancient scarabs" antes de "scarabs")
        if len(key) < 4:
            continue
        m = re.search(rf"(?<![\w']){re.escape(key)}(?![\w'])", text)
        if m:
            found.append(index[key])
            text = text[:m.start()] + " " * len(key) + text[m.end():]
    return list(dict.fromkeys(found))


# Hunts cujo nome no TibiaPal não bate com o wiki: área do wiki correspondente (conferida à mão).
PLACE_AREAS = [
    (r"azzilon walls", ["Azzilon Castle"]), (r"carnivora", ["Carnivora's Rocks"]), (r"^chor\b", ["Chor"]),
    (r"dessert dungeon", ["Dessert Dungeons"]), (r"^falcons", ["Falcon Bastion"]), (r"feyrist surface", ["Feyrist Meadows"]),
    (r"\bhive\b", ["Hive Outpost", "Hive Ground Floor"]), (r"krailos (ogres )?surface", ["Krailos Steppe"]),
    (r"^misguided", ["Misguided Camp"]), (r"^barkless", ["Barkless Cult Trial Zone"]), (r"^bulltaurs", ["Bulltaur Lair"]),
    (r"oramond west", ["OramondWestern Plains"]), (r"oramond minos", ["Oramond Minotaur Camp"]),
    (r"^prison -\d", ["Roshamuul Prison"]), (r"radiant ascend", ["Radiant Ascendancy"]),
    (r"(energy|fire|ice) library", ["Secret Library"]), (r"summer court", ["Court of Summer"]),
    (r"winter court", ["Court of Winter"]), (r"nimmersatt's (boss|bottom) floor", ["Nimmersatt's Breeding Ground"]),
    (r"alchemist center", ["Alchemist Quarter"]),
]
# Hunts com os monstros informados à mão (quest ou área sem página de hunt no wiki).
FERUMBRAS = ["Blightwalker", "Dark Torturer", "Demon", "Destroyer", "Fury", "Grimeleech", "Hand of Cursed Fate",
             "Hellfire Fighter", "Hellflayer", "Hellhound", "Juggernaut", "Nightmare", "Phantasm", "Plaguesmith",
             "Spectre", "Undead Dragon", "Vexclaw"]
PLACE_CREATURES = [
    (r"ferumbras", FERUMBRAS),
    # listas das páginas de região do wiki (Targuna, Ingol, Oramond)
    (r"targuna lizards", ["Lizard Executioner", "Lizard Henchman", "Lizard Magician", "Lizard Swordmaster"]),
    (r"targuna pirates", ["Pirate Cook", "Pirate Gunner", "Pirate Navigator", "Pirate Quartermaster"]),
    (r"targuna infernoids", ["Infernoid Blob", "Infernoid Hound", "Infernoid Soul", "Infernoid Spiritual"]),
    (r"^ingol(?![a-z])", ["Harpy", "Carnivostrich", "Liodile", "Rhindeer", "Crape Man", "Boar Man"]),
    (r"oramond catacombs", ["Metal Gargoyle", "Grim Reaper", "Demon"]),
    (r"oramond (mountain )?hideout", ["Glooth Bandit", "Glooth Brigand"]),
    (r"asura mirror|true asuras", ["True Dawnfire Asura", "True Frost Flower Asura", "True Midnight Asura"]),
    (r"werecreatures", ["Werewolf", "Werebear", "Wereboar", "Werebadger", "Werefox", "Werehyaena", "Werelion"]),
    (r"roshamuul (terrorsleep )?mines \(terrorsleeps\)|roshamuul terrorsleep mines", ["Terrorsleep"]),
]
# criaturas que não são de hunt comum: lembranças, versões de evento ou de quest
SPECIAL = re.compile(r"^(memory of|animated|neutral|little|dazed|mirror image|illusion|spirit of|echo of)\b", re.I)


def huntable(names: list[str], cdata: dict) -> list[str]:
    return [n for n in names if not cdata[n].get("boss") and not SPECIAL.search(n)]


def fits_level(names: list[str], cdata: dict, lvl: int | None) -> list[str]:
    """família de criaturas é uma pista solta: fica só o que faz sentido para o level da hunt (exp até 60x o level)."""
    if not lvl:
        return names
    cap = lvl * 60 + 300
    return [n for n in names if (cdata[n].get("exp") or 0) <= cap]
# palavras que não são nome de bicho (para a busca por família de criaturas)
NOT_CREATURE = set("""the of and cave caves surface lower upper west east north south mines mine raid active inactive floor boss
bottom only runes sanguine full lap castle seal seals way tower walls city library portal temple sun sea areas area
center centre stage inner outskirts dungeon tomb hideout mountain profit advanced entrance basement stealth ring sudden
death aoe island islands plains steppe central puzzle crypts crypt wildlife golem""".split())


def singular(w: str) -> str:
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if re.search(r"(x|s|sh|ch)es$", w):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 4:
        return w[:-1]
    return w


def family(place: str, names: list[str], skip: set[str]) -> list[str]:
    """"Coryms" -> Corym Charlatan, Corym Skirmisher...: criaturas com a palavra (no singular) no começo de uma palavra
    do nome. Tenta pares de palavras antes ("orc cults" -> Orc Cult...), depois palavras soltas."""
    words = [singular(w.replace("'s", "")) for w in re.findall(r"[a-z']+", place.lower())]
    keys = [f"{a} {b}" for a, b in zip(words, words[1:]) if a not in NOT_CREATURE and b not in NOT_CREATURE]
    keys += [w for w in words if len(w) >= 4 and w not in NOT_CREATURE and w not in skip]
    for k in keys:
        hits = [n for n in names if re.search(rf"(?<![\w']){re.escape(k)}", n.lower())]
        if hits:
            return hits[:15]
    return []


def main() -> None:
    places = tibiapal()
    areas = json.loads(AREAS.read_text(encoding="utf8"))
    index, cdata = creature_index()
    by_area = {a["name"]: a for a in areas["areas"]}
    area_names = sorted(areas["areas"], key=lambda a: len(a["name"]), reverse=True)
    cities = sorted({a["city"] for a in areas["areas"] if a["city"]}, key=len, reverse=True)
    city_words = {w for c in cities for w in c.lower().split()} | {"liberty", "bay", "port", "hope", "roshamuul", "issavi",
                                                                   "krailos", "oramond", "marapur", "targuna", "edron", "yalahar"}
    creature_names = sorted(cdata, key=len)
    out, used, slugs = [], set(), set()
    for p in places.values():
        name_l = p["name"].lower()
        manual = next((cs for pat, cs in PLACE_CREATURES if re.search(pat, name_l)), None)
        mapped = next((ns for pat, ns in PLACE_AREAS if re.search(pat, name_l)), None)
        area = by_area.get(mapped[0]) if mapped else next(
            (a for a in area_names if len(a["name"]) >= 4 and re.search(rf"(?<!\w){re.escape(a['name'].lower())}s?(?!\w)", name_l)), None)
        if manual:
            monsters = [c for c in manual if c in cdata]
        else:
            lvl = min((v["lvl"] for v in p["voc"].values() if v.get("lvl")), default=None)
            monsters = huntable(find_creatures(p["name"], index), cdata)
            if not monsters and area:
                pool = [c for n in (mapped or [area["name"]]) for c in by_area.get(n, {}).get("creatures", [])]
                monsters = huntable([c for c in dict.fromkeys(pool) if c in cdata], cdata)
            if not monsters:
                monsters = fits_level(huntable(family(p["name"], creature_names, city_words), cdata), cdata, lvl)
            monsters = relevant(monsters, cdata)
        words = re.findall(r"[a-z']+", name_l)
        city = ((area or {}).get("city") or next((c for c in cities if c.lower() in name_l), "")
                or next((CITY_ALIAS[w] for w in words if w in CITY_ALIAS), ""))
        slug = base = re.sub(r"[^a-z0-9]+", "-", p["name"].lower()).strip("-")
        n = 2
        while slug in slugs:  # dois locais com o mesmo endereço ganham sufixo
            slug, n = f"{base}-{n}", n + 1
        slugs.add(slug)
        row = {"slug": slug, "name": p["name"], "city": city, "voc": p["voc"], "creatures": monsters}
        if area:
            row["wiki_area"] = area["name"]
        if p.get("video"):
            row["video"] = p["video"]
        out.append(row)
        used.update(monsters)
    for n, img in wiki.images(sorted(used)).items():
        cdata[n]["img"] = img
    data = {
        "source": "TibiaPal (tibiapal.com/hunting) e TibiaWiki (tibia.fandom.com, CC BY-SA)",
        "updated": time.strftime("%Y-%m-%d"), "icons": areas["icons"],
        "places": out, "creatures": {n: cdata[n] for n in sorted(used)},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf8", newline="\n")
    print(f"{len(out)} locais; com monstros: {sum(1 for r in out if r['creatures'])}; "
          f"com área do wiki: {sum(1 for r in out if r.get('wiki_area'))}; monstros: {len(used)}; "
          f"sem monstro: {[r['name'] for r in out if not r['creatures']][:40]}")


if __name__ == "__main__":
    main()
