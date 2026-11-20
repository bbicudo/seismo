"""Gera collector/src/seismo_collector/data/raids.json a partir da TibiaWiki (CC BY-SA).

Uso: python tools/build_raid_seed.py
Lê as páginas da categoria Raids (uma por região), extrai cada raid e suas criaturas, e busca o
"spawntype" de cada criatura (Raid, Regular...). Rodar de novo quando a wiki ganhar raids novas.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Seismo/0.1 (Tibia fansite; raid seed builder)"}
API = "https://tibia.fandom.com/api.php"
OUT = Path(__file__).resolve().parents[1] / "collector/src/seismo_collector/data/raids.json"


def get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def clean(s: str) -> str:
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    return re.sub(r"'{2,}", "", s).strip()


def raids() -> list[dict]:
    members = get({"action": "query", "list": "categorymembers", "cmtitle": "Category:Raids", "cmlimit": 500})
    pages = [m["title"] for m in members["query"]["categorymembers"] if m["title"].endswith(" Raids") and "/" not in m["title"]]
    out, seen = [], set()
    for page in pages:
        region = page[: -len(" Raids")]
        text = get({"action": "parse", "page": page, "prop": "wikitext"})["parse"]["wikitext"]["*"]
        parts = re.split(r"^===\s*(.+?)\s*===\s*$", text, flags=re.M)
        for i in range(1, len(parts), 2):
            m = re.search(r"\{\{(?:Template:)?CreatureList\|(.*?)\}\}", parts[i + 1], flags=re.S)
            if not m:
                continue
            creatures = []
            for line in m.group(1).split("|"):
                name = clean(re.sub(r"\s*\(Creature\)\s*$", "", line.strip()))
                if name and "=" not in name and name not in creatures:
                    creatures.append(name)
            slug = re.sub(r"[^a-z0-9]+", "-", f"{region} {parts[i]}".lower()).strip("-")
            if creatures and slug not in seen:
                seen.add(slug)
                out.append({"slug": slug, "name": clean(parts[i]), "region": region, "creatures": creatures})
        time.sleep(0.5)
    return out


def spawntypes(names: list[str]) -> dict[str, str]:
    info: dict[str, str] = {}
    for i in range(0, len(names), 40):
        data = get({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                    "titles": "|".join(names[i:i + 40]), "redirects": 1})["query"]
        back = {}
        for key in ("normalized", "redirects"):
            for m in data.get(key, []):
                back[m["to"]] = back.get(m["from"], m["from"])
        for page in data["pages"].values():
            title = page.get("title")
            orig = back.get(back.get(title, title), back.get(title, title))
            text = (page.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("*", "")
            m = re.search(r"\|\s*spawntype\s*=\s*([^\n|]*)", text)
            info[orig] = m.group(1).strip() if m else ""
        time.sleep(0.5)
    return {n: info.get(n, "") for n in names}


def main() -> None:
    rs = raids()
    names = sorted({c for r in rs for c in r["creatures"]})
    data = {"source": "TibiaWiki (tibia.fandom.com), CC BY-SA 3.0", "raids": rs, "spawntype": spawntypes(names)}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rs)} raids, {len(names)} criaturas -> {OUT}")


if __name__ == "__main__":
    main()
