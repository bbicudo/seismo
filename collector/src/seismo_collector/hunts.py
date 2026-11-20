"""Áreas de caça (TibiaWiki): carrega data/hunts.json na tabela hunts. Não faz requisições."""

import json
from importlib import resources

from psycopg_pool import AsyncConnectionPool

from .raids import race_keys


def load_seed() -> list[dict]:
    raw = resources.files("seismo_collector").joinpath("data/hunts.json").read_text(encoding="utf-8")
    return json.loads(raw)["hunts"]


async def sync(pool: AsyncConnectionPool) -> int:
    hunts = load_seed()
    rows = [(h["slug"], h["name"], h["city"] or None, h["x"], h["y"], h["z"], h["creatures"],
             sorted({k for c in h["creatures"] for k in race_keys(c)})) for h in hunts]
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.executemany(
                    """
                    INSERT INTO hunts (slug, name, city, x, y, z, creatures, race_keys)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, city = EXCLUDED.city, x = EXCLUDED.x,
                      y = EXCLUDED.y, z = EXCLUDED.z, creatures = EXCLUDED.creatures, race_keys = EXCLUDED.race_keys
                    """,
                    rows,
                )
                await cur.execute("DELETE FROM hunts WHERE NOT (slug = ANY(%s))", ([r[0] for r in rows],))
    return len(rows)
