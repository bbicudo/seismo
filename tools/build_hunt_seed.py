"""Gera collector/src/seismo_collector/data/hunts.json a partir da TibiaWiki (CC BY-SA).

Uso: python tools/build_hunt_seed.py
Para cada página da categoria Hunting Places, pega o nome, a cidade, a posição no mapa (template Mapper Coords)
e todas as criaturas listadas (templates CreatureList). Hunts sem coordenadas ficam de fora do mapa.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Seismo/0.1 (Tibia fansite; hunt map builder)"}
API = "https://tibia.fandom.com/api.php"
OUT = Path(__file__).resolve().parents[1] / "collector/src/seismo_collector/data/hunts.json"
COORD_RE = re.compile(r"\{\{Mapper Coords\|(\d+)\.(\d+)\|(\d+)\.(\d+)\|(\d+)")


def get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.load(r)


def clean(s: str) -> str:
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    return re.sub(r"'{2,}|<[^>]+>", "", s).strip()


def field(text: str, name: str) -> str:
    m = re.search(rf"\|\s*{name}\s*=\s*(.*)", text)
    return clean(m.group(1)) if m else ""


def parse(title: str, text: str) -> dict | None:
    if "{{Infobox Hunt" not in text:
        return None
    m = COORD_RE.search(text)
    creatures: list[str] = []
    for block in re.findall(r"\{\{CreatureList\|(.*?)\}\}", text, flags=re.S):
        for line in block.split("|"):
            name = clean(re.sub(r"\s*\(Creature\)\s*$", "", line.strip()))
            if name and "=" not in name and name not in creatures:
                creatures.append(name)
    if not m or not creatures:
        return None
    x = int(m[1]) * 256 + int(m[2])
    y = int(m[3]) * 256 + int(m[4])
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return {"slug": slug, "name": field(text, "name") or title, "city": field(text, "city"),
            "x": x, "y": y, "z": int(m[5]), "creatures": creatures}


def main() -> None:
    members = get({"action": "query", "list": "categorymembers", "cmtitle": "Category:Hunting Places", "cmlimit": 500})
    titles = [m["title"] for m in members["query"]["categorymembers"] if m["ns"] == 0 and m["title"] != "Hunting Places"]
    hunts = []
    for i in range(0, len(titles), 40):
        data = get({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                    "titles": "|".join(titles[i:i + 40])})["query"]
        for page in data["pages"].values():
            text = (page.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("*", "")
            h = parse(page["title"], text)
            if h:
                hunts.append(h)
        time.sleep(0.5)
    hunts.sort(key=lambda h: h["name"])
    data = {"source": "TibiaWiki (tibia.fandom.com), CC BY-SA 3.0", "hunts": hunts}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"{len(titles)} páginas, {len(hunts)} hunts com coordenadas e criaturas -> {OUT}")


if __name__ == "__main__":
    main()
