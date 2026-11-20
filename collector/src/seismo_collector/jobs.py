"""Coletas diárias: kill statistics (base das raids), casas e leilões, lista de guilds e detalhes de guild.

Rodam numa tarefa separada, um pedido por vez, e esperam sempre que a rodada de online estiver em
andamento (a foto de 5 em 5 minutos tem prioridade). Cada coleta diária roda uma vez por dia de jogo,
15 minutos depois do server save. Detalhes de guild e de casa andam aos poucos, o dia todo.
"""

import asyncio
import logging
import time
from datetime import date, datetime, timedelta, timezone

from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from . import events, raids
from .logic import game_day
from .privacy import Optouts, process_queue
from .settings import Settings
from .tibiadata import NotFound, TibiaData

log = logging.getLogger("seismo.jobs")

TOWNS = [
    "Ab'Dendriel", "Ankrahmun", "Carlin", "Darashia", "Edron", "Farmine", "Gray Beach", "Issavi",
    "Kazordoon", "Liberty Bay", "Moonfall", "Port Hope", "Rathleton", "Silvertides", "Svargrond",
    "Thais", "Venore", "Yalahar",
]
SAVE_MARGIN = timedelta(minutes=15)
# coleta diária -> feature flag que a controla (área administrativa)
JOB_FLAGS = {
    "events": "collect_events",
    "killstats": "collect_killstats",
    "raids": "collect_killstats",
    "guild_lists": "collect_guilds",
    "houses": "collect_houses",
}
STATS_TTL = 35 * 86400


def parse_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


class DailyJobs:
    def __init__(self, settings: Settings, redis: Redis, pool: AsyncConnectionPool, td: TibiaData,
                 online_idle: asyncio.Event, optouts: Optouts):
        self.s = settings
        self.redis = redis
        self.pool = pool
        self.td = td
        self.online_idle = online_idle
        self.optouts = optouts

    # ---------- infraestrutura ----------
    async def call(self, coro_fn, *args):
        """Espera a rodada de online terminar (e a pausa acabar) antes de cada pedido."""
        while await self.paused():
            await asyncio.sleep(15)
        await self.online_idle.wait()
        return await coro_fn(*args)

    async def paused(self) -> bool:
        return (await self.redis.get("seismo:paused")) == "1"

    def effective_day(self) -> date:
        return game_day(datetime.now(timezone.utc) - SAVE_MARGIN)

    async def worlds(self) -> list[tuple[int, str]]:
        async with self.pool.connection() as conn:
            cur = await conn.execute("SELECT id, name FROM worlds ORDER BY name")
            rows = await cur.fetchall()
        names = set(self.s.target_worlds([n for _, n in rows]))
        return [(wid, n) for wid, n in rows if n in names]

    async def record(self, job: str, day: date, items: int, seconds: float) -> None:
        pipe = self.redis.pipeline(transaction=False)
        pipe.set(f"seismo:job:{job}:day", day.isoformat())
        pipe.set(f"seismo:job:{job}:items", items)
        pipe.set(f"seismo:job:{job}:seconds", f"{seconds:.0f}")
        pipe.set(f"seismo:job:{job}:finished_at", datetime.now(timezone.utc).isoformat())
        await pipe.execute()
        log.info("coleta %s do dia %s: %d itens em %.0fs", job, day, items, seconds)

    async def run_forever(self) -> None:
        log.info("coletas diárias iniciadas")
        while True:
            try:
                if await self.paused():
                    await asyncio.sleep(15)
                    continue
                worked = await self.step()
            except Exception:
                log.exception("coleta diária falhou; nova tentativa em 5 min")
                await asyncio.sleep(300)
                continue
            if not worked:
                await asyncio.sleep(60)

    async def step(self) -> bool:
        # pedidos de opt-out têm prioridade sobre qualquer coleta diária
        if await process_queue(self.pool, self.redis, self.td, self.optouts, self.call):
            return True
        await self.optouts.refresh()
        flags = await self.flags()
        day = self.effective_day()
        for job, fn in (("events", self.job_events), ("killstats", self.job_killstats), ("raids", self.job_raids),
                        ("guild_lists", self.job_guild_lists), ("houses", self.job_houses),
                        ("retention", self.job_retention)):
            flag = JOB_FLAGS.get(job)
            if flag and not flags.get(flag, True):
                continue  # desligada na área administrativa: volta a rodar quando for religada
            if await self.redis.get(f"seismo:job:{job}:day") != day.isoformat():
                t0 = time.monotonic()
                items = await fn(day)
                await self.record(job, day, items, time.monotonic() - t0)
                return True
        if flags.get("collect_guilds", True) and await self.guild_details_batch(day):
            return True
        if flags.get("collect_houses", True) and await self.house_details_batch(day):
            return True
        return False

    async def flags(self) -> dict[str, bool]:
        async with self.pool.connection() as conn:
            cur = await conn.execute("SELECT key, enabled FROM feature_flags")
            return {k: v for k, v in await cur.fetchall()}

    # ---------- eventos e destaques do dia (poucas requisições) ----------
    async def job_events(self, day: date) -> int:
        return await events.collect(self.pool, self.td, self.call, day, self.s.user_agent)

    # ---------- raids (sem requisições: usa as kill statistics já gravadas) ----------
    async def job_raids(self, day: date) -> int:
        return await raids.detect(self.pool, day)

    # ---------- retenção (política de privacidade) ----------
    async def job_retention(self, day: date) -> int:
        """Minutos por dia ficam 400 dias; pedidos de opt-out vencidos e não confirmados, 30 dias."""
        async with self.pool.connection() as conn:
            cur = await conn.execute("DELETE FROM daily_online WHERE game_day < %s", (day - timedelta(days=400),))
            removed = cur.rowcount
            cur = await conn.execute(
                "DELETE FROM optout_requests WHERE status <> 'verified' AND expires_at < now() - interval '30 days'"
            )
            removed += cur.rowcount
        return removed

    # ---------- kill statistics ----------
    async def job_killstats(self, day: date) -> int:
        stats_day = day - timedelta(days=1)   # "last day" = o dia que fechou no último server save
        total = 0
        for wid, name in await self.worlds():
            try:
                entries = await self.call(self.td.killstatistics, name)
            except NotFound:
                continue
            rows = [
                (wid, stats_day, e["race"], int(e.get("last_day_killed") or 0), int(e.get("last_day_players_killed") or 0))
                for e in entries
                if e.get("race") and (e.get("last_day_killed") or e.get("last_day_players_killed"))
            ]
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.executemany(
                        """
                        INSERT INTO kill_stats_daily (world_id, stats_day, race, killed, players_killed)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (world_id, stats_day, race) DO UPDATE
                          SET killed = EXCLUDED.killed, players_killed = EXCLUDED.players_killed
                        """,
                        rows,
                    )
            total += len(rows)
        return total

    # ---------- guilds ----------
    async def job_guild_lists(self, day: date) -> int:
        total = 0
        for wid, name in await self.worlds():
            data = await self.call(self.td.guilds, name)
            rows = []
            for in_formation, key in ((False, "active"), (True, "formation")):
                for g in data.get(key) or []:
                    if g.get("name"):
                        rows.append((g["name"], wid, in_formation, g.get("logo_url"), day, day))
            async with self.pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cur:
                        await cur.executemany(
                            """
                            INSERT INTO guilds (name, world_id, in_formation, logo_url, first_seen_day, last_seen_day)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (name) DO UPDATE SET
                              world_id = EXCLUDED.world_id, in_formation = EXCLUDED.in_formation,
                              logo_url = EXCLUDED.logo_url, last_seen_day = EXCLUDED.last_seen_day,
                              disbanded_day = NULL
                            """,
                            rows,
                        )
                        await cur.execute(
                            """
                            UPDATE guilds SET disbanded_day = %s
                            WHERE world_id = %s AND last_seen_day < %s AND disbanded_day IS NULL
                            """,
                            (day, wid, day),
                        )
            total += len(rows)
        return total

    async def guild_details_batch(self, day: date, limit: int = 25) -> bool:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT g.id, g.name, g.details_fetched_at IS NOT NULL AS known
                FROM guilds g
                WHERE g.disbanded_day IS NULL
                  AND (g.details_fetched_at IS NULL OR g.details_fetched_at < now() - make_interval(days => %s))
                ORDER BY g.details_fetched_at NULLS FIRST
                LIMIT %s
                """,
                (self.s.guild_refresh_days, limit),
            )
            due = await cur.fetchall()
        for gid, name, known in due:
            try:
                g = await self.call(self.td.guild, name)
            except NotFound:
                g = {}
            await self.save_guild(gid, g, day, known)
            await self.count("guild_details")
        return bool(due)

    async def save_guild(self, gid: int, g: dict, day: date, known: bool) -> None:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    if not g.get("name"):
                        await cur.execute(
                            "UPDATE guilds SET disbanded_day = COALESCE(disbanded_day, %s), details_fetched_at = now() WHERE id = %s",
                            (day, gid),
                        )
                        return
                    halls = g.get("guildhalls") or []
                    await cur.execute(
                        """
                        UPDATE guilds SET founded = %s, members_total = %s, in_war = %s, open_applications = %s,
                               guildhalls = %s, details_fetched_at = now()
                        WHERE id = %s
                        """,
                        (parse_day(g.get("founded")), g.get("members_total"), g.get("in_war"),
                         g.get("open_applications"), len(halls), gid),
                    )
                    members = {m["name"]: m for m in g.get("members") or []
                               if m.get("name") and m["name"] not in self.optouts}
                    await cur.execute("SELECT name FROM guild_members WHERE guild_id = %s", (gid,))
                    before = {r[0] for r in await cur.fetchall()}
                    joins = sorted(members.keys() - before)
                    leaves = sorted(before - members.keys())
                    if leaves:
                        await cur.execute("DELETE FROM guild_members WHERE guild_id = %s AND name = ANY(%s)", (gid, leaves))
                    if members:
                        await cur.executemany(
                            """
                            INSERT INTO guild_members (guild_id, name, rank, title, vocation, level, joined)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (guild_id, name) DO UPDATE SET rank = EXCLUDED.rank, title = EXCLUDED.title,
                              vocation = EXCLUDED.vocation, level = EXCLUDED.level, joined = EXCLUDED.joined
                            """,
                            [(gid, n, m.get("rank"), m.get("title"), m.get("vocation"), m.get("level"),
                              parse_day(m.get("joined"))) for n, m in members.items()],
                        )
                    if known:  # na primeira leitura não existem "entradas": é só o retrato inicial
                        events = [(gid, n, "join", day) for n in joins] + [(gid, n, "leave", day) for n in leaves]
                        if events:
                            await cur.executemany(
                                "INSERT INTO guild_events (guild_id, name, event, event_day) VALUES (%s, %s, %s, %s)",
                                events,
                            )

    # ---------- casas ----------
    async def job_houses(self, day: date) -> int:
        total = 0
        for wid, world in await self.worlds():
            for town in TOWNS:
                try:
                    data = await self.call(self.td.houses, world, town)
                except NotFound:
                    continue
                items = [(h, "house") for h in data.get("house_list") or []] + \
                        [(h, "guildhall") for h in data.get("guildhall_list") or []]
                if items:
                    await self.save_houses(wid, town, items, day)
                total += len(items)
        return total

    async def save_houses(self, wid: int, town: str, items: list, day: date) -> None:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.executemany(
                        """
                        INSERT INTO houses (world_id, house_id, town, name, kind, size, rent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (world_id, house_id) DO UPDATE SET
                          town = EXCLUDED.town, name = EXCLUDED.name, kind = EXCLUDED.kind,
                          size = EXCLUDED.size, rent = EXCLUDED.rent
                        """,
                        [(wid, h["house_id"], town, h.get("name") or "", kind, h.get("size"), h.get("rent"))
                         for h, kind in items],
                    )
                    ids = [h["house_id"] for h, _ in items]
                    await cur.execute(
                        """
                        SELECT DISTINCT ON (house_id) house_id, rented, auctioned, auction_finished
                        FROM house_snapshots
                        WHERE world_id = %s AND house_id = ANY(%s) AND snap_day < %s
                        ORDER BY house_id, snap_day DESC
                        """,
                        (wid, ids, day),
                    )
                    prev = {r[0]: r[1:] for r in await cur.fetchall()}
                    snaps, changed = [], []
                    for h, _ in items:
                        a = h.get("auction") or {}
                        rented, auctioned = bool(h.get("rented")), bool(h.get("auctioned"))
                        finished = bool(a.get("finished"))
                        snaps.append((wid, h["house_id"], day, rented, auctioned, a.get("current_bid") or None,
                                      a.get("time_left") or None, finished))
                        p = prev.get(h["house_id"])
                        if p is None or p[0] != rented or (finished and not p[2]):
                            changed.append(h["house_id"])
                    await cur.executemany(
                        """
                        INSERT INTO house_snapshots (world_id, house_id, snap_day, rented, auctioned, current_bid,
                                                     time_left, auction_finished)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (world_id, house_id, snap_day) DO UPDATE SET
                          rented = EXCLUDED.rented, auctioned = EXCLUDED.auctioned,
                          current_bid = EXCLUDED.current_bid, time_left = EXCLUDED.time_left,
                          auction_finished = EXCLUDED.auction_finished
                        """,
                        snaps,
                    )
                    if changed:  # mudou de situação: vale ler o detalhe (dono) de novo
                        await cur.execute(
                            "UPDATE houses SET needs_details = true WHERE world_id = %s AND house_id = ANY(%s)",
                            (wid, changed),
                        )

    async def house_details_batch(self, day: date, limit: int = 25) -> bool:
        used = int(await self.redis.get(f"seismo:count:house_details:{day.isoformat()}") or 0)
        if used >= self.s.house_detail_daily_budget:
            return False
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT h.world_id, w.name, h.house_id
                FROM houses h JOIN worlds w ON w.id = h.world_id
                WHERE h.needs_details
                ORDER BY h.details_fetched_at NULLS FIRST, h.world_id, h.house_id
                LIMIT %s
                """,
                (min(limit, self.s.house_detail_daily_budget - used),),
            )
            due = await cur.fetchall()
        for wid, world, hid in due:
            try:
                d = await self.call(self.td.house, world, hid)
            except NotFound:
                d = {}
            await self.save_house_detail(wid, hid, d, day)
            await self.count("house_details")
        return bool(due)

    async def save_house_detail(self, wid: int, hid: int, d: dict, day: date) -> None:
        status = d.get("status") or {}
        owner = ((status.get("rental") or {}).get("owner") or "").strip() if status.get("is_rented") else ""
        if owner and owner in self.optouts:
            owner = ""  # quem fez opt-out não entra no histórico de donos
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE houses SET beds = COALESCE(%s, beds), needs_details = false, details_fetched_at = now() "
                        "WHERE world_id = %s AND house_id = %s",
                        (d.get("beds"), wid, hid),
                    )
                    await cur.execute(
                        "SELECT id, owner FROM house_owners WHERE world_id = %s AND house_id = %s AND ended_day IS NULL",
                        (wid, hid),
                    )
                    current = await cur.fetchone()
                    if current and current[1] == owner:
                        await cur.execute("UPDATE house_owners SET last_seen_day = %s WHERE id = %s", (day, current[0]))
                        return
                    if current:
                        await cur.execute("UPDATE house_owners SET ended_day = %s WHERE id = %s", (day, current[0]))
                    if owner:
                        await cur.execute(
                            "INSERT INTO house_owners (world_id, house_id, owner, first_seen_day, last_seen_day) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (wid, hid, owner, day, day),
                        )

    async def count(self, what: str) -> None:
        key = f"seismo:count:{what}:{self.effective_day().isoformat()}"
        pipe = self.redis.pipeline(transaction=False)
        pipe.incr(key)
        pipe.expire(key, STATS_TTL)
        await pipe.execute()
