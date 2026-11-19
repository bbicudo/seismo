import asyncio
import logging
import signal

from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from .cycle import Collector
from .jobs import DailyJobs
from .privacy import Optouts
from .settings import Settings


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = Settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    pool = AsyncConnectionPool(settings.postgres_dsn, min_size=1, max_size=6, open=False)
    await pool.open(wait=True)
    optouts = Optouts(pool)
    await optouts.refresh(force=True)
    collector = Collector(settings, redis, pool, optouts)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    tasks = [asyncio.create_task(collector.run_forever())]
    if settings.daily_jobs_enabled:
        jobs = DailyJobs(settings, redis, pool, collector.td, collector.online_idle, optouts)
        tasks.append(asyncio.create_task(jobs.run_forever()))
    await stop.wait()
    logging.getLogger("seismo.collector").info("encerrando")
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await collector.td.close()
    await pool.close()
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
