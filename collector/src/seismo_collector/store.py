"""Gravação no Postgres. Regra de privacidade: nenhum horário de presença por personagem é gravado,
só totais de minutos por dia de jogo, o último dia visto e contadores anônimos."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from psycopg_pool import AsyncConnectionPool

from .logic import Diff, activity_counts, decode_player, game_day, hour_bucket


async def upsert_worlds(pool: AsyncConnectionPool, worlds: list[dict[str, Any]], ts: datetime) -> dict[str, int]:
    rows = [
        (
            w["name"], w.get("location"), w.get("pvp_type"), bool(w.get("battleye_protected")),
            w.get("transfer_type"), w.get("game_world_type"), int(w.get("players_online") or 0), ts,
        )
        for w in worlds
    ]
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO worlds (name, location, pvp_type, battleye_protected, transfer_type,
                                    game_world_type, players_online, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                  location = EXCLUDED.location, pvp_type = EXCLUDED.pvp_type,
                  battleye_protected = EXCLUDED.battleye_protected, transfer_type = EXCLUDED.transfer_type,
                  game_world_type = EXCLUDED.game_world_type, players_online = EXCLUDED.players_online,
                  updated_at = EXCLUDED.updated_at
                """,
                rows,
            )
            await cur.execute("SELECT name, id FROM worlds")
            ids = {name: wid for name, wid in await cur.fetchall()}
            await cur.executemany(
                """
                INSERT INTO world_online_5m (world_id, ts, players_online) VALUES (%s, %s, %s)
                ON CONFLICT (world_id, ts) DO UPDATE SET players_online = EXCLUDED.players_online
                """,
                [(ids[r[0]], ts, r[6]) for r in rows],
            )
    return ids


@dataclass
class WorldBatch:
    world_id: int
    ts: datetime
    curr: dict[str, str]
    upsert_names: list[str] = field(default_factory=list)          # logins + mudanças de level/vocação
    diff: Diff = field(default_factory=Diff)
    sessions: dict[str, dict[date, int]] = field(default_factory=dict)  # logouts: minutos por dia
    transfers: list[tuple[str, int]] = field(default_factory=list)      # (nome, world_id de origem)


async def write_world(pool: AsyncConnectionPool, b: WorldBatch) -> None:
    today = game_day(b.ts)
    month = today.replace(day=1)
    hour = hour_bucket(b.ts)
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                if b.upsert_names:
                    rows = []
                    for name in b.upsert_names:
                        level, vocation = decode_player(b.curr[name])
                        rows.append((name, b.world_id, level, vocation, today, today, level))
                    # first_level só é gravado na primeira vez (o UPDATE abaixo não mexe nele)
                    await cur.executemany(
                        """
                        INSERT INTO characters (name, world_id, level, vocation, first_seen_day, last_seen_day, first_level)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (name) DO UPDATE SET
                          world_id = EXCLUDED.world_id, level = EXCLUDED.level,
                          vocation = EXCLUDED.vocation, last_seen_day = EXCLUDED.last_seen_day
                        """,
                        rows,
                    )
                if b.diff.level_changes:
                    await cur.executemany(
                        """
                        INSERT INTO monthly_level (character_id, month, level_start, level_end)
                        SELECT id, %s, %s, %s FROM characters WHERE name = %s
                        ON CONFLICT (character_id, month) DO UPDATE SET level_end = EXCLUDED.level_end
                        """,
                        [(month, old, new, name) for name, old, new in b.diff.level_changes],
                    )
                if b.sessions:
                    rows = [(day, minutes, name) for name, days in b.sessions.items() for day, minutes in days.items()]
                    await cur.executemany(
                        """
                        INSERT INTO daily_online (character_id, game_day, minutes)
                        SELECT id, %s, %s FROM characters WHERE name = %s
                        ON CONFLICT (character_id, game_day) DO UPDATE
                          SET minutes = daily_online.minutes + EXCLUDED.minutes
                        """,
                        rows,
                    )
                    await cur.executemany(
                        "UPDATE characters SET last_seen_day = GREATEST(last_seen_day, %s) WHERE name = %s",
                        [(max(days) if days else today, name) for name, days in b.sessions.items()],
                    )
                if b.transfers:
                    await cur.executemany(
                        """
                        INSERT INTO transfers (character_id, from_world_id, to_world_id, detected_day)
                        SELECT id, %s, %s, %s FROM characters WHERE name = %s
                        ON CONFLICT DO NOTHING
                        """,
                        [(src, b.world_id, today, name) for name, src in b.transfers],
                    )
                counts = activity_counts(b.curr)
                if counts:
                    await cur.executemany(
                        """
                        INSERT INTO activity_buckets (world_id, hour, vocation, level_band, samples)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (world_id, hour, vocation, level_band)
                          DO UPDATE SET samples = activity_buckets.samples + EXCLUDED.samples
                        """,
                        [(b.world_id, hour, voc, band, n) for (voc, band), n in counts.items()],
                    )
                await cur.execute(
                    """
                    INSERT INTO world_hour_snapshots (world_id, hour, snapshots) VALUES (%s, %s, 1)
                    ON CONFLICT (world_id, hour) DO UPDATE SET snapshots = world_hour_snapshots.snapshots + 1
                    """,
                    (b.world_id, hour),
                )
