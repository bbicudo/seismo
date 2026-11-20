"""Eventos do jogo e destaques do dia.

- Double XP, double skill e rapid respawn: lidos das notícias do tibia.com pela TibiaData. As notícias trazem
  a janela no formato "Between the server saves of November 20 and November 23" (dias de jogo 20, 21 e 22).
- Calendário comunitário (lua cheia, Lightbearer, eventos sazonais): api.tibiamarket.top/events.
- Criatura e chefe em destaque do dia: TibiaData (/creatures e /boostablebosses).
Tudo isso custa poucas requisições por dia.
"""

import logging
import re
from datetime import date, datetime, timedelta

import httpx
from psycopg_pool import AsyncConnectionPool

from .tibiadata import TibiaData

log = logging.getLogger("seismo.events")

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], start=1)}
SAVES_RE = re.compile(
    r"server saves? (?:of|on) (?P<m1>[A-Z][a-z]+) (?P<d1>\d{1,2})(?:st|nd|rd|th)? and (?:the )?"
    r"(?:(?P<m2>[A-Z][a-z]+) )?(?P<d2>\d{1,2})(?:st|nd|rd|th)?",
)
CALENDAR_URL = "https://api.tibiamarket.top/events"


def normalize(text: str) -> str:
    """As notícias do tibia.com usam espaço não separável (\\xa0) no meio das frases."""
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " "))


def event_kinds(title: str, text: str) -> list[str]:
    s = normalize(f"{title} {text}").lower()
    kinds = []
    if "double xp" in s or "double experience" in s or "twice the usual amount of experience" in s:
        kinds.append("double_xp")
    if "double skill" in s or "skill training" in s and "twice as fast" in s:
        kinds.append("double_skill")
    if "rapid respawn" in s:
        kinds.append("rapid_respawn")
    return kinds


def parse_window(text: str, published: date) -> list[date]:
    """Dias de jogo entre dois server saves citados no texto da notícia (o dia do segundo save não entra)."""
    m = SAVES_RE.search(normalize(text))
    if not m:
        return []
    m1 = MONTHS.get(m["m1"].lower())
    m2 = MONTHS.get((m["m2"] or m["m1"]).lower())
    if not m1 or not m2:
        return []
    start = date(published.year + (1 if m1 < published.month - 6 else 0), m1, int(m["d1"]))
    end = date(start.year + (1 if m2 < m1 else 0), m2, int(m["d2"]))
    if not (0 < (end - start).days <= 14):
        return []
    return [start + timedelta(days=i) for i in range((end - start).days)]


async def collect(pool: AsyncConnectionPool, td: TibiaData, call, today: date, user_agent: str) -> int:
    rows: list[tuple] = []

    # 1) notícias recentes do tibia.com com double ou rapid respawn
    try:
        latest = (await call(td.get, "news/latest")).get("news") or []
    except Exception as exc:  # noqa: BLE001 - notícia é opcional, não pode derrubar a coleta
        log.warning("notícias indisponíveis: %s", exc)
        latest = []
    for n in latest:
        title = n.get("news") or ""
        if not any(k in title.lower() for k in ("double", "rapid respawn", "event")):
            continue
        try:
            item = (await call(td.get, f"news/id/{n['id']}")).get("news") or {}
        except Exception:  # noqa: BLE001
            continue
        text = item.get("content") or ""
        kinds = event_kinds(title, text)
        published = date.fromisoformat((n.get("date") or today.isoformat())[:10])
        for day in parse_window(text, published):
            for kind in kinds:
                label = {"double_xp": "Double XP", "double_skill": "Double Skill", "rapid_respawn": "Rapid Respawn"}[kind]
                rows.append((day, label, kind, "tibia.com", item.get("url") or n.get("url")))

    # 2) calendário comunitário: 7 dias para trás e 30 para frente
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": user_agent}) as client:
            r = await client.get(CALENDAR_URL, params={"start_days_ago": 7, "end_days_ago": -30})
            r.raise_for_status()
            for d in r.json():
                day = datetime.fromisoformat(d["date"]).date()
                for name in d.get("events") or []:
                    rows.append((day, name, "calendar", "tibiamarket", "https://tibiamarket.top"))
    except Exception as exc:  # noqa: BLE001
        log.warning("calendário comunitário indisponível: %s", exc)

    # 3) criatura e chefe em destaque hoje
    boosted_creature = boosted_boss = None
    try:
        boosted_creature = ((await call(td.get, "creatures")).get("creatures") or {}).get("boosted", {}).get("name")
        boosted_boss = ((await call(td.get, "boostablebosses")).get("boostable_bosses") or {}).get("boosted", {}).get("name")
    except Exception as exc:  # noqa: BLE001
        log.warning("destaques do dia indisponíveis: %s", exc)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if rows:
                await cur.executemany(
                    """
                    INSERT INTO game_events (day, name, kind, source, url) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (day, name) DO UPDATE SET kind = EXCLUDED.kind, source = EXCLUDED.source, url = EXCLUDED.url
                    """,
                    rows,
                )
            if boosted_creature or boosted_boss:
                await cur.execute(
                    """
                    INSERT INTO daily_boosted (day, creature, boss) VALUES (%s, %s, %s)
                    ON CONFLICT (day) DO UPDATE SET creature = EXCLUDED.creature, boss = EXCLUDED.boss
                    """,
                    (today, boosted_creature, boosted_boss),
                )
    log.info("eventos: %d dias de evento registrados; destaque do dia: %s / %s", len(rows), boosted_creature, boosted_boss)
    return len(rows)
