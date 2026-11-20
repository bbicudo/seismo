"""Detecção de raids pelas kill statistics.

A lista de raids e criaturas vem da TibiaWiki (data/raids.json). Uma criatura só "denuncia" uma raid se for
rara no dia a dia: morta em menos de 20% dos dias×mundos dos últimos 28 dias. Assim demônios ou monks (que
existem o tempo todo) não contam, mas draptors, yetis ou um chefe como Ghazbaran contam. Raids formadas só por
criaturas comuns não são detectáveis e ficam de fora.
"""

import json
import logging
from datetime import date, timedelta
from importlib import resources

from psycopg_pool import AsyncConnectionPool

log = logging.getLogger("seismo.raids")
RARE_FRACTION = 0.20
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


def load_seed() -> list[dict]:
    raw = resources.files("seismo_collector").joinpath("data/raids.json").read_text(encoding="utf-8")
    return json.loads(raw)["raids"]


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
            cur = await conn.execute("SELECT id, race_keys FROM raids")
            raids = await cur.fetchall()
            for raid_id, keys in raids:
                # chave nunca vista conta como rara: se um dia aparecer, é sinal de raid
                signature = [k for k in keys if frequency.get(k, 0.0) < RARE_FRACTION]
                await conn.execute("UPDATE raids SET signature = %s WHERE id = %s", (signature, raid_id))
            # reprocessa os dias da janela: as assinaturas podem ter mudado com mais histórico
            await conn.execute("DELETE FROM raid_occurrences WHERE day >= %s", (since,))
            cur = await conn.execute(
                """
                INSERT INTO raid_occurrences (world_id, raid_id, day, kills)
                SELECT k.world_id, r.id, k.stats_day, sum(k.killed + k.players_killed)::int
                FROM raids r
                JOIN kill_stats_daily k ON lower(k.race) = ANY(r.signature)
                WHERE k.stats_day >= %s AND k.killed > 0 AND cardinality(r.signature) > 0
                GROUP BY k.world_id, r.id, k.stats_day
                ON CONFLICT DO NOTHING
                """,
                (since,),
            )
            inserted = cur.rowcount
    log.info("raids: %d ocorrências na janela de %d dias", inserted, WINDOW_DAYS)
    return inserted
