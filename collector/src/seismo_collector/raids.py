"""Detecção de raids pelas kill statistics.

A lista de raids e criaturas vem da TibiaWiki (data/raids.json), junto com o "spawn type" de cada criatura.
Uma criatura "denuncia" a raid quando a wiki diz que ela só nasce em raid (Raid sem Regular), como Midnight
Panther ou Yeti. Quando a wiki não informa, ela só conta se for rara no dia a dia: morta em menos de 5% dos
dias×mundos dos últimos 28 dias (assim um chefe como Ghazbaran conta, mas monks não). Raids feitas só de
criaturas que também nascem normalmente (orcs, wasps) não são detectáveis.

Além disso, num mundo com pelo menos 7 dias de histórico, uma criatura morta na maioria dos dias daquele mundo
(um chefe caçado todo dia, por exemplo) também não conta como raid ali.
"""

import json
import logging
from datetime import date, timedelta
from importlib import resources

from psycopg_pool import AsyncConnectionPool

log = logging.getLogger("seismo.raids")
RARE_FRACTION = 0.05     # fração máxima de dias×mundos em que a criatura aparece
LOCAL_DAILY = 0.5        # num mundo, aparecer em mais da metade dos dias = rotina, não raid
LOCAL_MIN_DAYS = 7       # a regra local só vale com essa quantidade de dias de histórico no mundo
WINDOW_DAYS = 28


def race_keys(creature: str) -> list[str]:
    """Formas que o nome pode ter nas kill statistics: chefes no singular, criaturas comuns no plural."""
    n = creature.lower().strip()
    keys = {n, n + "s", n + "es"}
    if n.endswith("y") and len(n) > 1 and n[-2] not in "aeiou":
        keys.add(n[:-1] + "ies")
    if n.endswith("fe"):
        keys.add(n[:-2] + "ves")
    elif n.endswith("f"):
        keys.add(n[:-1] + "ves")
    if n.endswith("man"):
        keys.add(n[:-3] + "men")
    if n.endswith("mouse"):
        keys.add(n[:-5] + "mice")
    return sorted(keys)


def _seed() -> dict:
    raw = resources.files("seismo_collector").joinpath("data/raids.json").read_text(encoding="utf-8")
    return json.loads(raw)


def load_seed() -> list[dict]:
    return _seed()["raids"]


def spawn_kind(spawntype: str) -> str:
    s = spawntype.lower()
    if not s:
        return "unknown"
    return "raid" if "raid" in s and "regular" not in s else "regular"


async def sync_seed(pool: AsyncConnectionPool) -> int:
    rows = []
    for r in load_seed():
        keys = sorted({k for c in r["creatures"] for k in race_keys(c)})
        rows.append((r["slug"], r["name"], r["region"], r["creatures"], keys))
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO raids (slug, name, region, creatures, race_keys) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, region = EXCLUDED.region,
                  creatures = EXCLUDED.creatures, race_keys = EXCLUDED.race_keys
                """,
                rows,
            )
    return len(rows)


async def detect(pool: AsyncConnectionPool, today: date) -> int:
    """Recalcula as assinaturas e grava ocorrências para todos os dias com kill statistics que ainda não têm."""
    await sync_seed(pool)
    since = today - timedelta(days=WINDOW_DAYS)
    async with pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "SELECT count(DISTINCT (world_id, stats_day)) FROM kill_stats_daily WHERE stats_day >= %s", (since,)
            )
            total = (await cur.fetchone())[0] or 0
            if not total:
                return 0
            cur = await conn.execute(
                """
                SELECT lower(race), count(*) FROM kill_stats_daily
                WHERE stats_day >= %s AND killed > 0 GROUP BY 1
                """,
                (since,),
            )
            frequency = {race: n / total for race, n in await cur.fetchall()}
            seed = _seed()
            kinds = {name: spawn_kind(st) for name, st in seed.get("spawntype", {}).items()}
            cur = await conn.execute("SELECT id, slug FROM raids")
            ids = {slug: rid for rid, slug in await cur.fetchall()}
            for r in seed["raids"]:
                signature: set[str] = set()
                for creature in r["creatures"]:
                    kind = kinds.get(creature, "unknown")
                    keys = race_keys(creature)
                    if kind == "raid":
                        signature.update(keys)
                    elif kind == "unknown":
                        # sem informação na wiki: só conta se for rara (chave nunca vista também conta)
                        signature.update(k for k in keys if frequency.get(k, 0.0) < RARE_FRACTION)
                if r["slug"] in ids:
                    await conn.execute("UPDATE raids SET signature = %s WHERE id = %s",
                                       (sorted(signature), ids[r["slug"]]))
            # reprocessa os dias da janela: as assinaturas podem ter mudado com mais histórico
            await conn.execute("DELETE FROM raid_occurrences WHERE day >= %s", (since,))
            cur = await conn.execute(
                """
                WITH world_days AS (
                  SELECT world_id, count(DISTINCT stats_day) AS n FROM kill_stats_daily
                  WHERE stats_day >= %s GROUP BY world_id
                ),
                local AS (
                  SELECT k.world_id, lower(k.race) AS race, count(*)::float / wd.n AS freq, wd.n
                  FROM kill_stats_daily k JOIN world_days wd ON wd.world_id = k.world_id
                  WHERE k.stats_day >= %s AND k.killed > 0 GROUP BY k.world_id, lower(k.race), wd.n
                )
                INSERT INTO raid_occurrences (world_id, raid_id, day, kills)
                SELECT k.world_id, r.id, k.stats_day, sum(k.killed + k.players_killed)::int
                FROM raids r
                JOIN kill_stats_daily k ON lower(k.race) = ANY(r.signature)
                JOIN local l ON l.world_id = k.world_id AND l.race = lower(k.race)
                WHERE k.stats_day >= %s AND k.killed > 0 AND cardinality(r.signature) > 0
                  AND NOT (l.n >= %s AND l.freq > %s)
                GROUP BY k.world_id, r.id, k.stats_day
                ON CONFLICT DO NOTHING
                """,
                (since, since, since, LOCAL_MIN_DAYS, LOCAL_DAILY),
            )
            inserted = cur.rowcount
    log.info("raids: %d ocorrências na janela de %d dias", inserted, WINDOW_DAYS)
    return inserted
