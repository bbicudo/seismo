"""Opt-out: lista de quem saiu do Seismo e verificação do código no comentário do personagem."""

import logging
import time

from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from .tibiadata import NotFound, TibiaData

log = logging.getLogger("seismo.privacy")
OPTOUT_QUEUE = "seismo:optout:queue"


class Optouts:
    """Nomes (em minúsculas) de quem fez opt-out. Recarregado do banco no máximo a cada 60 s."""

    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool
        self.names: set[str] = set()
        self._loaded = 0.0

    async def refresh(self, force: bool = False) -> set[str]:
        if force or time.monotonic() - self._loaded > 60:
            async with self.pool.connection() as conn:
                cur = await conn.execute("SELECT lower(name) FROM privacy_optouts")
                self.names = {r[0] for r in await cur.fetchall()}
            self._loaded = time.monotonic()
        return self.names

    def __contains__(self, name: str) -> bool:
        return name.lower() in self.names


async def purge(pool: AsyncConnectionPool, name: str) -> None:
    """Apaga tudo que liga o nome a dados no Seismo. Os agregados anônimos ficam (não identificam ninguém)."""
    async with pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM characters WHERE lower(name) = lower(%s)", (name,))  # cascata: minutos, levels, transfers
            await conn.execute("DELETE FROM guild_members WHERE lower(name) = lower(%s)", (name,))
            await conn.execute("DELETE FROM guild_events WHERE lower(name) = lower(%s)", (name,))
            await conn.execute("DELETE FROM house_owners WHERE lower(owner) = lower(%s)", (name,))


async def process_queue(pool: AsyncConnectionPool, redis: Redis, td: TibiaData, optouts: Optouts, call) -> bool:
    """Confere um pedido da fila. Devolve True se havia algo para fazer."""
    name = await redis.lpop(OPTOUT_QUEUE)
    if not name:
        return False
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id, code FROM optout_requests WHERE lower(name) = lower(%s) ORDER BY created_at DESC LIMIT 1",
            (name,),
        )
        req = await cur.fetchone()
    if not req:
        return True
    req_id, code = req
    try:
        char = await call(td.character, name)
    except (NotFound, RuntimeError):
        char = {}
    status, message, canonical = "failed", None, name
    if not char.get("name"):
        message = "personagem não encontrado (ou TibiaData indisponível); tente de novo em alguns minutos"
    elif code.lower() not in (char.get("comment") or "").lower():
        message = "código não encontrado no comentário do personagem"
    else:
        status, canonical = "verified", char["name"]
    async with pool.connection() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE optout_requests SET status = %s, message = %s, attempts = attempts + 1, checked_at = now() "
                "WHERE id = %s",
                (status, message, req_id),
            )
            if status == "verified":
                await conn.execute(
                    "INSERT INTO privacy_optouts (name) VALUES (%s) ON CONFLICT DO NOTHING", (canonical,)
                )
    if status == "verified":
        await purge(pool, canonical)
        await optouts.refresh(force=True)
        log.info("opt-out confirmado e dados apagados")
    else:
        log.info("opt-out não confirmado: %s", message)
    return True
