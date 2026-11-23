"""Gera web/data/hunt-places.json: locais de caça testados pelo TibiaPal cruzados com os monstros do TibiaWiki.

Uso: python tools/build_hunt_places.py  (depois de tools/build_hunt_areas.py, que gera as áreas do wiki)

- TibiaPal (tibiapal.com/hunting, por Kusnier, usado com autorização e crédito): para cada vocação, level mínimo,
  exp crua e loot por hora, arma/munição/estilo recomendado e o vídeo do teste. Uma consulta à página.
- TibiaWiki (CC BY-SA): os monstros de cada local, achados pelo nome no plural ("Swamp Trolls" -> Swamp Troll) ou,
  se o local cita uma área do wiki e nenhum monstro, pelos monstros dessa área. Fraquezas e dano de cada monstro.
"""
import html
import json
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
            name = re.sub(r"\s+", " ", txt[1])
            entry = {"lvl": wiki.num(txt[0]), "exp": money(txt[2]), "loot": money(txt[3])}
            extra = txt[4] if len(txt) > 4 and txt[4] not in ("", "-", "N/A") else None
            if extra:
                entry["extra"] = extra
            place = places.setdefault(name, {"name": name, "voc": {}})
            place["voc"][voc] = entry
            if video and "video" not in place:
                place["video"] = video.group(1)
    return places


def creature_index() -> dict[str, str]:
    """nome em minúsculas (singular e plural) -> nome da criatura, para todas as criaturas do wiki."""
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
    text = re.sub(r"\(.*?\)|-\d+|\+\d+", " ", place).lower()
    found = []
    for key in sorted(index, key=len, reverse=True):  # o nome mais longo primeiro ("ancient scarabs" antes de "scarabs")
        if len(key) < 4:
            continue
        m = re.search(rf"(?<![\w']){re.escape(key)}(?![\w'])", text)
        if m:
            found.append(index[key])
            text = text[:m.start()] + " " * len(key) + text[m.end():]
    return list(dict.fromkeys(found))


def main() -> None:
    places = tibiapal()
    areas = json.loads(AREAS.read_text(encoding="utf8"))
    index, cdata = creature_index()
    area_names = sorted(areas["areas"], key=lambda a: len(a["name"]), reverse=True)
    cities = sorted({a["city"] for a in areas["areas"] if a["city"]}, key=len, reverse=True)
    out, used, slugs = [], set(), set()
    for p in places.values():
        name_l = p["name"].lower()
        area = next((a for a in area_names if len(a["name"]) > 5 and a["name"].lower() in name_l), None)
        monsters = find_creatures(p["name"], index)
        if not monsters and area:
            monsters = [c for c in area["creatures"] if c in cdata]
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
