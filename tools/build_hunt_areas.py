"""Gera web/data/hunt-areas.json a partir da TibiaWiki (CC BY-SA) para o utilitário de áreas de caça.

Uso: python tools/build_hunt_areas.py
- Áreas: páginas da categoria Hunting Places com Infobox Hunt (cidade, levels recomendados, notas de exp e loot)
  e as criaturas dos templates CreatureList (listas sob um título "Boss" viram bosses).
- Criaturas: Infobox Creature (hp, exp, quanto apanham de cada elemento e o dano máximo por elemento).
- Imagens: só o caminho no CDN do wiki; quem carrega é o navegador do visitante.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (compatible; wiki-reader/1.0)"}
API = "https://tibia.fandom.com/api.php"
CDN = "https://static.wikia.nocookie.net/tibia/images/"
OUT = Path(__file__).resolve().parents[1] / "web/data/hunt-areas.json"
ELEMENTS = ["physical", "fire", "ice", "earth", "energy", "holy", "death"]
DAMAGE = ELEMENTS + ["lifedrain", "manadrain", "drown"]


def get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if attempt == 2:
                raise
            time.sleep(3)


def pages(titles: list[str]) -> dict[str, str]:
    """wikitext de cada título (segue redirects; a chave é o título pedido)."""
    out = {}
    for i in range(0, len(titles), 20):  # lotes pequenos: com muitos, a API corta o conteúdo de algumas páginas
        d = get({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "redirects": 1,
                 "titles": "|".join(titles[i:i + 20])})["query"]
        back = {n["to"]: n["from"] for n in d.get("normalized", [])}
        for r in d.get("redirects", []):
            back[r["to"]] = back.get(r["from"], r["from"])
        for p in d.get("pages", {}).values():
            if p.get("revisions"):
                out[back.get(p["title"], p["title"])] = p["revisions"][0]["slots"]["main"]["*"]
        time.sleep(0.5)
    missing = [t for t in titles if t not in out]
    for t in missing:  # o que ainda faltou vai um por um
        got = pages_one(t)
        if got:
            out[t] = got
    return out


def pages_one(title: str) -> str | None:
    d = get({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "redirects": 1,
             "titles": title})["query"]
    for p in d.get("pages", {}).values():
        if p.get("revisions"):
            return p["revisions"][0]["slots"]["main"]["*"]
    return None


def images(names: list[str]) -> dict[str, str]:
    """caminho do .gif de cada nome no CDN do wiki (sem o prefixo)."""
    out = {}
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        d = get({"action": "query", "prop": "imageinfo", "iiprop": "url", "redirects": 1,
                 "titles": "|".join(f"File:{n}.gif" for n in batch)})["query"]
        back = {n["to"]: n["from"] for n in d.get("normalized", [])}
        for r in d.get("redirects", []):
            back[r["to"]] = back.get(r["from"], r["from"])
        for p in d.get("pages", {}).values():
            if p.get("imageinfo"):
                url = p["imageinfo"][0]["url"]
                title = back.get(p["title"], p["title"])
                if url.startswith(CDN):
                    out[title[5:-4]] = url[len(CDN):].replace("&path-prefix=en", "")
        time.sleep(0.5)
    return out


def clean(s: str) -> str:
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    return re.sub(r"'{2,}|<[^>]+>", "", s).strip()


def field(text: str, name: str) -> str:
    m = re.search(rf"^\|\s*{name}\s*=[ \t]*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def num(s: str) -> int | None:
    m = re.search(r"-?\d+", s.replace(",", "").replace(".", ""))
    return int(m.group(0)) if m else None


def parse_area(title: str, text: str) -> dict | None:
    if "{{Infobox Hunt" not in text:
        return None
    creatures, bosses = [], []
    # cada CreatureList pertence ao título (== ... ==) mais próximo acima dele
    for m in re.finditer(r"\{\{CreatureList\|(.*?)\}\}", text, flags=re.S):
        heads = re.findall(r"^=+\s*(.*?)\s*=+\s*$", text[:m.start()], flags=re.M)
        is_boss = bool(heads) and "boss" in heads[-1].lower()
        for line in m.group(1).split("|"):
            name = clean(re.sub(r"\s*\(Creature\)\s*$", "", line.strip()))
            if not name or "=" in name:
                continue
            target = bosses if is_boss else creatures
            if name not in creatures and name not in bosses:
                target.append(name)
    if not creatures:
        return None
    lvl = {k: num(field(text, f"lvl{v}")) for k, v in (("k", "knights"), ("p", "paladins"), ("m", "mages"))}
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return {
        "slug": slug, "name": clean(field(text, "name")) or title,
        "city": {"Ab'dendriel": "Ab'Dendriel"}.get(clean(field(text, "city")), clean(field(text, "city"))),
        "lvl": {k: v for k, v in lvl.items() if v}, "exp": num(field(text, "expstar")), "loot": num(field(text, "lootstar")),
        "creatures": creatures, "bosses": bosses,
    }


ELEMENT_ALIAS = {"physical": "physical", "fire": "fire", "ice": "ice", "earth": "earth", "poison": "earth",
                 "energy": "energy", "holy": "holy", "death": "death", "life drain": "lifedrain",
                 "lifedrain": "lifedrain", "mana drain": "manadrain", "manadrain": "manadrain",
                 "drowning": "drown", "drown": "drown"}


def ability_damage(text: str) -> dict:
    out: dict[str, int] = {}
    for lo_hi in re.findall(r"\{\{Melee\|([^|}]*)", text):
        hi = re.findall(r"\d+", lo_hi.replace(",", ""))
        if hi:
            out["physical"] = out.get("physical", 0) + int(hi[-1])
    for args in re.findall(r"\{\{Ability\|((?:[^{}]|\{\{[^{}]*\}\})*)\}\}", text):
        parts = [x.strip() for x in re.split(r"\|(?![^\[]*\]\])", args)]
        el = next((x.split("=", 1)[1].strip().lower() for x in parts if x.startswith("element=")), "")
        el = ELEMENT_ALIAS.get(el)
        rng = next((x for x in parts[1:] if re.fullmatch(r"\d[\d,]*\s*-\s*\d[\d,]*\+?", x)), None)
        if el and rng:
            out[el] = out.get(el, 0) + int(re.findall(r"\d+", rng.replace(",", ""))[-1])
    return out


def parse_creature(text: str) -> dict | None:
    if "{{Infobox Creature" not in text:
        return None
    mods = {}
    for e in ELEMENTS:
        v = num(field(text, f"{e}DmgMod"))
        if v is not None:
            mods[e] = v
    dmg = {}
    m = re.search(r"\{\{Max Damage\|([^}]*)\}\}", text)
    if m:
        for part in m.group(1).split("|"):
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip().lower().replace(" ", "")
                k = {"drowning": "drown", "lifesteal": "lifedrain"}.get(k, k)
                n = num(v)
                if k in DAMAGE and n:
                    dmg[k] = n
    if not dmg:  # sem Max Damage: soma o máximo de cada habilidade (corpo a corpo = físico)
        dmg = ability_damage(text)
    if not mods:
        return None
    return {"hp": num(field(text, "hp")), "exp": num(field(text, "exp")),
            "boss": field(text, "isboss").lower().startswith("yes"), "mods": mods, "dmg": dmg}


def main() -> None:
    d = get({"action": "query", "list": "categorymembers", "cmtitle": "Category:Hunting Places", "cmlimit": 500})
    titles = [m["title"] for m in d["query"]["categorymembers"] if m["ns"] == 0 and m["title"] != "Hunting Places"]
    areas = [a for t, txt in sorted(pages(titles).items()) if (a := parse_area(t, txt))]
    names = sorted({c for a in areas for c in a["creatures"] + a["bosses"]})
    texts = pages(names)
    for n, txt in list(texts.items()):  # página de desambiguação (ex.: Monk) aponta para "Monk (Creature)"
        m = re.search(r"disambig_title=([^|}]*\(Creature\))", txt)
        if "{{Infobox Creature" not in txt and m:
            texts[n] = pages_one(m.group(1).strip()) or txt
    creatures = {n: c for n, txt in texts.items() if (c := parse_creature(txt))}
    for n, img in images(list(creatures)).items():
        creatures[n]["img"] = img
    icons = images([f"{e.capitalize()} Protection Icon" for e in ELEMENTS])
    for a in areas:  # o que não é criatura no wiki (coordenada, sala, chave) sai da lista
        a["creatures"] = [c for c in a["creatures"] if c in creatures]
        a["bosses"] = [c for c in a["bosses"] if c in creatures]
    areas = [a for a in areas if a["creatures"]]
    data = {"source": "TibiaWiki (tibia.fandom.com), CC BY-SA", "updated": time.strftime("%Y-%m-%d"),
            "icons": {e: icons.get(f"{e.capitalize()} Protection Icon") for e in ELEMENTS},
            "areas": areas, "creatures": creatures}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf8", newline="\n")
    print(f"{len(areas)} áreas, {len(creatures)} de {len(names)} criaturas com dados, "
          f"{sum('img' in c for c in creatures.values())} com sprite, ícones: {sum(1 for v in data['icons'].values() if v)}/7")


if __name__ == "__main__":
    main()
