"""Laço principal: a cada intervalo, uma foto de cada mundo, o diff contra a foto anterior e a gravação."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from . import store
from .logic import cycle_slot, diff_snapshots, encode_player, split_minutes
from .privacy import Optouts
from .settings import Settings
from .tibiadata import NotFound, TibiaData

log = logging.getLogger("seismo.collector")

PAUSED_KEY = "seismo:paused"
LOGIN_TTL = 2 * 86400       # marca de login (só no Redis, nunca no banco)
LASTWORLD_TTL = 86400       # para detectar transfer em até 24 h
STATS_TTL = 35 * 86400


class Collector:
    def __init__(self, settings: Settings, redis: Redis, pool: AsyncConnectionPool, optouts: Optouts):
        self.s = settings
        self.redis = redis
        self.pool = pool
        self.optouts = optouts
        # aberto quando não há rodada de online em andamento (as coletas diárias esperam por ele)
        self.online_idle = asyncio.Event()
        self.online_idle.set()
        self.td = TibiaData(
            settings.tibiadata_base,
            settings.user_agent,
            max_concurrency=settings.max_concurrency,
            max_rps=settings.max_rps,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            on_request=self._count_request,
        )

    async def _count_request(self, ok: bool) -> None:
        day = datetime.now(timezone.utc).date().isoformat()
        key = f"seismo:{'requests' if ok else 'errors'}:{day}"
        pipe = self.redis.pipeline(transaction=False)
        pipe.incr(key)
        pipe.expire(key, STATS_TTL)
        if not ok:  # pedido que falhou também conta como requisição feita
            pipe.incr(f"seismo:requests:{day}")
            pipe.expire(f"seismo:requests:{day}", STATS_TTL)
        await pipe.execute()

    async def paused(self) -> bool:
        return (await self.redis.get(PAUSED_KEY)) == "1"

    async def run_forever(self) -> None:
        if not await self.redis.exists(PAUSED_KEY):
            await self.redis.set(PAUSED_KEY, "1" if self.s.seismo_paused else "0")
        log.info("coletor iniciado (%s) | UA: %s", self.s.seismo_env, self.s.user_agent)
        announced_pause = False
        while True:
            if await self.paused():
                if not announced_pause:
                    log.info("pausado: aguardando 'seismo.sh resume'")
                    announced_pause = True
                await asyncio.sleep(15)
                continue
            announced_pause = False
            started = time.monotonic()
            slot = cycle_slot(datetime.now(timezone.utc), self.s.collect_interval_seconds)
            self.online_idle.clear()
            try:
                await self.run_cycle(slot)
            except Exception:
                log.exception("rodada falhou")
            finally:
                self.online_idle.set()
            elapsed = time.monotonic() - started
            now = datetime.now(timezone.utc).timestamp()
            next_slot = slot.timestamp() + self.s.collect_interval_seconds
            wait = max(5.0, next_slot - now)
            log.info("rodada levou %.1fs; próxima em %.0fs", elapsed, wait)
            await asyncio.sleep(wait)

    async def run_cycle(self, ts: datetime) -> None:
        t0 = time.monotonic()
        await self.optouts.refresh()
        worlds = await self.td.worlds()
        ids = await store.upsert_worlds(self.pool, worlds, ts)
        targets = self.s.target_worlds([w["name"] for w in worlds])
        results = await asyncio.gather(*(self.collect_world(name, ids, ts) for name in targets), return_exceptions=True)
        failed = [name for name, r in zip(targets, results) if isinstance(r, Exception)]
        for name, r in zip(targets, results):
            if isinstance(r, Exception) and not isinstance(r, NotFound):
                log.warning("mundo %s falhou: %s", name, r)
        seconds = time.monotonic() - t0
        pipe = self.redis.pipeline(transaction=False)
        pipe.set("seismo:last_cycle_at", ts.isoformat())
        pipe.set("seismo:last_cycle_seconds", f"{seconds:.1f}")
        pipe.set("seismo:last_cycle_worlds", f"{len(targets) - len(failed)}/{len(targets)}")
        await pipe.execute()
        log.info("rodada %s: %d/%d mundos em %.1fs", ts.isoformat(), len(targets) - len(failed), len(targets), seconds)

    async def collect_world(self, name: str, ids: dict[str, int], ts: datetime) -> None:
        players = await self.td.world_online(name)
        curr = {p["name"]: encode_player(int(p.get("level") or 0), p.get("vocation") or "None") for p in players}
        key = f"online:{name}"
        prev = await self.redis.hgetall(key)
        last = await self.redis.get(f"lastsnap:{name}")
        stale = last is None or ts.timestamp() - float(last) > self.s.stale_after_seconds
        if stale and prev:
            log.info("%s: foto anterior velha demais; reiniciando sessões sem somar minutos", name)
        base = {} if stale else prev
        d = diff_snapshots(base, curr)

        # sessões encerradas: lê o início (só no Redis) e converte em minutos por dia de jogo
        sessions = {}
        if d.logouts:
            starts = await self.redis.mget([f"login:{n}" for n in d.logouts])
            for n, started in zip(d.logouts, starts):
                if started:
                    begin = datetime.fromtimestamp(float(started), tz=timezone.utc)
                    sessions[n] = split_minutes(begin, ts)

        # transfers: entrou aqui e tinha saído de outro mundo nas últimas 24 h
        transfers = []
        if d.logins:
            lastworlds = await self.redis.mget([f"lastworld:{n}" for n in d.logins])
            for n, lw in zip(d.logins, lastworlds):
                if lw and lw != name and lw in ids:
                    transfers.append((n, ids[lw]))

        # opt-out: nada ligado ao nome vai para o banco (a foto no Redis e os contadores anônimos continuam)
        out = self.optouts
        sessions = {n: v for n, v in sessions.items() if n not in out}
        transfers = [t for t in transfers if t[0] not in out]
        d.level_changes = [c for c in d.level_changes if c[0] not in out]
        changed = {n for n, _, _ in d.level_changes} | {n for n, _ in d.vocation_changes if n not in out}
        batch = store.WorldBatch(
            world_id=ids[name], ts=ts, curr=curr,
            upsert_names=sorted({n for n in d.logins if n not in out} | changed), diff=d,
            sessions=sessions, transfers=transfers,
        )
        await store.write_world(self.pool, batch)

        # só depois do banco gravado, atualiza o estado no Redis
        pipe = self.redis.pipeline(transaction=True)
        if stale:
            for n in prev:
                if n not in curr:
                    pipe.delete(f"login:{n}")
        for n in d.logouts:
            pipe.delete(f"login:{n}")
            pipe.set(f"lastworld:{n}", name, ex=LASTWORLD_TTL)
        for n in d.logins:
            pipe.set(f"login:{n}", str(ts.timestamp()), ex=LOGIN_TTL)
        pipe.delete(key)
        if curr:
            pipe.hset(key, mapping=curr)
        pipe.set(f"lastsnap:{name}", str(ts.timestamp()))
        await pipe.execute()
