"""Cliente da TibiaData com limite de concorrência, teto de pedidos por segundo e backoff."""

import asyncio
import logging
import random
import time
from typing import Any, Awaitable, Callable
from urllib.parse import quote as _quote

import httpx
import orjson

log = logging.getLogger("seismo.tibiadata")

RETRY_STATUS = {429, 500, 502, 503, 504}


def quote(part: str) -> str:
    """Escapa um pedaço de URL (nomes com espaço e apóstrofo, como Ab'Dendriel)."""
    return _quote(part, safe="")


class NotFound(Exception):
    pass


class RateLimiter:
    """Garante um intervalo mínimo entre o início de dois pedidos (teto global de req/s)."""

    def __init__(self, max_rps: float):
        self.min_interval = 1.0 / max_rps if max_rps > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now < self._next:
                await asyncio.sleep(self._next - now)
                now = time.monotonic()
            self._next = now + self.min_interval


class TibiaData:
    def __init__(
        self,
        base: str,
        user_agent: str,
        *,
        max_concurrency: int = 2,
        max_rps: float = 2.0,
        timeout: float = 20.0,
        max_retries: int = 4,
        on_request: Callable[..., Awaitable[None]] | None = None,
    ):
        self.base = base.rstrip("/")
        self.max_retries = max_retries
        self._sem = asyncio.Semaphore(max_concurrency)
        self._limiter = RateLimiter(max_rps)
        self._on_request = on_request
        self._client = httpx.AsyncClient(
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=timeout,
            http2=False,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, max_retries: int | None = None) -> dict[str, Any]:
        url = f"{self.base}/{path.lstrip('/')}"
        retries = self.max_retries if max_retries is None else max_retries
        attempt = 0
        while True:
            async with self._sem:
                await self._limiter.wait()
                try:
                    r = await self._client.get(url)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    status, retry_after, error = None, None, exc
                else:
                    status, retry_after, error = r.status_code, r.headers.get("retry-after"), None
            ok = status is not None and 200 <= status < 300
            if self._on_request:
                # tipo de consulta (primeiro trecho do caminho) e motivo, sem nomes: vira o detalhamento no /admin
                reason = None if ok else (str(status) if status is not None else type(error).__name__)
                await self._on_request(ok, path.lstrip("/").split("/")[0], reason)
            if ok:
                return orjson.loads(r.content)
            if status == 404:
                raise NotFound(url)
            retryable = error is not None or status in RETRY_STATUS
            if not retryable or attempt >= retries:
                raise RuntimeError(f"GET {url} falhou: status={status} erro={error!r}")
            delay = 2 ** (attempt + 1) + random.uniform(0, 1)
            if retry_after and retry_after.isdigit():
                delay = max(delay, min(float(retry_after), 120.0))
            log.warning("GET %s -> %s; nova tentativa em %.1fs", url, status or error, delay)
            await asyncio.sleep(delay)
            attempt += 1

    async def worlds(self) -> list[dict[str, Any]]:
        data = await self.get("worlds")
        return data.get("worlds", {}).get("regular_worlds") or []

    async def world_online(self, name: str) -> list[dict[str, Any]]:
        data = await self.get(f"world/{quote(name)}")
        return data.get("world", {}).get("online_players") or []

    async def killstatistics(self, world: str) -> list[dict[str, Any]]:
        data = await self.get(f"killstatistics/{quote(world)}")
        return data.get("killstatistics", {}).get("entries") or []

    async def houses(self, world: str, town: str) -> dict[str, Any]:
        data = await self.get(f"houses/{quote(world)}/{quote(town)}")
        return data.get("houses") or {}

    async def house(self, world: str, house_id: int) -> dict[str, Any]:
        data = await self.get(f"house/{quote(world)}/{house_id}")
        return data.get("house") or {}

    async def guilds(self, world: str) -> dict[str, Any]:
        data = await self.get(f"guilds/{quote(world)}")
        return data.get("guilds") or {}

    async def character(self, name: str) -> dict[str, Any]:
        # a TibiaData responde 502 para personagem inexistente: uma tentativa extra basta
        data = await self.get(f"character/{quote(name)}", max_retries=1)
        return (data.get("character") or {}).get("character") or {}

    async def guild(self, name: str) -> dict[str, Any]:
        data = await self.get(f"guild/{quote(name)}")
        return data.get("guild") or {}
