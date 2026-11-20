"""Aplica no coletor, sem reiniciar, os parâmetros ajustados na área administrativa (tabela app_settings).

Sem linha na tabela, vale o que veio do .env (ou o padrão do código). A validação de intervalos é feita pela API
ao gravar; aqui só convertemos o tipo e ignoramos valores estranhos.
"""

import asyncio
import json
import logging
import time

from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from . import raids
from .settings import Settings
from .tibiadata import TibiaData

log = logging.getLogger("seismo.params")

# parâmetro -> (onde fica, nome, tipo)
SETTINGS_KEYS = {
    "daily_request_cap": int, "collect_interval_seconds": int, "max_concurrency": int, "max_rps": float,
    "guild_refresh_days": int, "house_detail_daily_budget": int, "seismo_worlds": str, "retention_days": int,
}
RAIDS_KEYS = {"raids_rare_fraction": ("RARE_FRACTION", float), "raids_local_daily": ("LOCAL_DAILY", float),
              "raids_local_min_days": ("LOCAL_MIN_DAYS", int)}

_state = {"at": 0.0, "base": None}


async def apply(pool: AsyncConnectionPool, redis: Redis, settings: Settings, td: TibiaData, force: bool = False) -> None:
    if not force and time.monotonic() - _state["at"] < 30:
        return
    _state["at"] = time.monotonic()
    if _state["base"] is None:  # valores do .env / padrão, para voltar a eles quando o admin limpar
        _state["base"] = {k: getattr(settings, k) for k in SETTINGS_KEYS} | \
                         {k: getattr(raids, attr) for k, (attr, _) in RAIDS_KEYS.items()}
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT key, value FROM app_settings")
        stored = {k: v for k, v in await cur.fetchall()}
    values = dict(_state["base"])
    for k, v in stored.items():
        typ = SETTINGS_KEYS.get(k) or (RAIDS_KEYS[k][1] if k in RAIDS_KEYS else None)
        if typ is None:
            continue
        try:
            values[k] = typ(v)
        except (TypeError, ValueError):
            log.warning("parâmetro %s com valor inválido: %r", k, v)

    old_conc, old_rps = settings.max_concurrency, settings.max_rps
    for k in SETTINGS_KEYS:
        setattr(settings, k, values[k])
    for k, (attr, _) in RAIDS_KEYS.items():
        setattr(raids, attr, values[k])
    if settings.max_concurrency != old_conc:
        td._sem = asyncio.Semaphore(settings.max_concurrency)
        log.info("pedidos simultâneos: %d", settings.max_concurrency)
    if settings.max_rps != old_rps:
        td._limiter.min_interval = 1.0 / settings.max_rps if settings.max_rps > 0 else 0.0
        log.info("teto de pedidos por segundo: %.2f", settings.max_rps)
    await redis.set("seismo:params:effective", json.dumps(values), ex=600)
