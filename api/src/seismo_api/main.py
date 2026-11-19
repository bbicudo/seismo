"""API de leitura do Seismo. No lab: status do coletor, mundos e agregados anônimos.
Nenhuma rota devolve dados por personagem."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import ORJSONResponse
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from . import __version__
from .settings import Settings

settings = Settings()
MIN_CELL = 5  # célula anônima com menos de 5 pessoas não é mostrada


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = AsyncConnectionPool(settings.postgres_dsn, min_size=1, max_size=5, open=False,
                                         kwargs={"row_factory": dict_row})
    await app.state.pool.open(wait=True)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.pool.close()
    await app.state.redis.aclose()


app = FastAPI(title="Seismo API", version=__version__, lifespan=lifespan,
              default_response_class=ORJSONResponse, root_path="/api")


async def query(sql: str, *params) -> list[dict]:
    async with app.state.pool.connection() as conn:
        cur = await conn.execute(sql, params)
        return await cur.fetchall()


def cache(response: Response, seconds: int) -> None:
    response.headers["Cache-Control"] = f"public, max-age={seconds}"


@app.get("/healthz")
async def healthz():
    await query("SELECT 1")
    await app.state.redis.ping()
    return {"ok": True}


@app.get("/v1/status")
async def status(response: Response):
    r = app.state.redis
    day = datetime.now(timezone.utc).date().isoformat()
    keys = ["seismo:paused", "seismo:last_cycle_at", "seismo:last_cycle_seconds", "seismo:last_cycle_worlds",
            f"seismo:requests:{day}", f"seismo:errors:{day}"]
    paused, last_at, last_s, last_w, reqs, errs = await r.mget(keys)
    counts = (await query(
        """
        SELECT (SELECT count(*) FROM worlds) AS worlds,
               (SELECT count(*) FROM characters) AS characters,
               (SELECT max(ts) FROM world_online_5m) AS last_snapshot,
               (SELECT pg_database_size(current_database())) AS db_bytes
        """
    ))[0]
    jobs = {}
    for job in ("killstats", "guild_lists", "houses"):
        d, items, secs, fin = await r.mget([f"seismo:job:{job}:{k}" for k in ("day", "items", "seconds", "finished_at")])
        jobs[job] = {"day": d, "items": int(items or 0), "seconds": int(secs or 0), "finished_at": fin}
    progress = (await query(
        """
        SELECT (SELECT count(*) FROM guilds WHERE disbanded_day IS NULL) AS guilds,
               (SELECT count(*) FROM guilds WHERE disbanded_day IS NULL AND details_fetched_at IS NOT NULL) AS guilds_read,
               (SELECT count(*) FROM houses) AS houses,
               (SELECT count(*) FROM houses WHERE details_fetched_at IS NOT NULL) AS houses_read,
               (SELECT count(*) FROM kill_stats_daily) AS kill_rows
        """
    ))[0]
    cache(response, 15)
    return {
        "env": settings.seismo_env,
        "daily_jobs": jobs,
        "progress": progress,
        "collector": {
            "paused": paused == "1",
            "last_cycle_at": last_at,
            "last_cycle_seconds": float(last_s) if last_s else None,
            "last_cycle_worlds": last_w,
            "requests_today_utc": int(reqs or 0),
            "errors_today_utc": int(errs or 0),
        },
        "database": counts,
    }


@app.get("/v1/worlds")
async def worlds(response: Response):
    rows = await query(
        """
        SELECT name, location, pvp_type, battleye_protected, transfer_type, players_online, updated_at
        FROM worlds ORDER BY players_online DESC, name
        """
    )
    cache(response, 60)
    return rows


@app.get("/v1/worlds/{name}")
async def world(name: str, response: Response):
    found = await query("SELECT id, name, location, pvp_type, players_online, updated_at FROM worlds WHERE lower(name) = lower(%s)", name)
    if not found:
        raise HTTPException(404, "mundo não encontrado")
    w = found[0]
    series = await query(
        """
        SELECT ts, players_online FROM world_online_5m
        WHERE world_id = %s AND ts > now() - interval '48 hours' ORDER BY ts
        """,
        w["id"],
    )
    # composição anônima de quem está online agora, a partir da foto atual no Redis
    online = await app.state.redis.hvals(f"online:{w['name']}")
    comp: dict[str, dict[str, int]] = {}
    for value in online:
        level_s, _, voc = value.partition("|")
        level = int(level_s or 0)
        band = "1-99" if level < 100 else "100-299" if level < 300 else "300-599" if level < 600 else "600+"
        comp.setdefault(voc or "None", {}).setdefault(band, 0)
        comp[voc or "None"][band] += 1
    composition = [
        {"vocation": voc, "level_band": band, "players": n if n >= MIN_CELL else None}
        for voc, bands in sorted(comp.items()) for band, n in sorted(bands.items())
    ]
    wid = w.pop("id")
    kills = await query(
        """
        SELECT race, killed, players_killed, stats_day FROM kill_stats_daily
        WHERE world_id = %s AND stats_day = (SELECT max(stats_day) FROM kill_stats_daily WHERE world_id = %s)
        ORDER BY killed DESC LIMIT 15
        """,
        wid, wid,
    )
    houses = await query(
        """
        SELECT h.town,
               count(*) AS total,
               count(*) FILTER (WHERE s.rented) AS rented,
               count(*) FILTER (WHERE s.auctioned) AS auctioned
        FROM houses h
        JOIN LATERAL (SELECT rented, auctioned FROM house_snapshots s
                      WHERE s.world_id = h.world_id AND s.house_id = h.house_id
                      ORDER BY snap_day DESC LIMIT 1) s ON true
        WHERE h.world_id = %s
        GROUP BY h.town ORDER BY h.town
        """,
        wid,
    )
    guilds = await query(
        """
        SELECT name, members_total, in_war, open_applications, founded
        FROM guilds WHERE world_id = %s AND disbanded_day IS NULL
        ORDER BY members_total DESC NULLS LAST, name LIMIT 30
        """,
        wid,
    )
    guild_moves = await query(
        """
        SELECT count(*) FILTER (WHERE e.event = 'join') AS joins, count(*) FILTER (WHERE e.event = 'leave') AS leaves
        FROM guild_events e JOIN guilds g ON g.id = e.guild_id
        WHERE g.world_id = %s AND e.event_day > current_date - 7
        """,
        wid,
    )
    cache(response, 60)
    return {**w, "series_48h": series, "online_now": len(online), "composition": composition, "min_cell": MIN_CELL,
            "kills_last_day": kills, "houses_by_town": houses, "guilds": guilds, "guild_moves_7d": guild_moves[0]}


# ---------------------------------------------------------------- site v1

VOCATION_GROUPS = {  # vocação base -> nomes que a TibiaData usa
    "knight": ["Knight", "Elite Knight"], "paladin": ["Paladin", "Royal Paladin"],
    "sorcerer": ["Sorcerer", "Master Sorcerer"], "druid": ["Druid", "Elder Druid"],
    "monk": ["Monk", "Exalted Monk"], "none": ["None"],
}
BANDS = {"1-99", "100-299", "300-599", "600+"}
ALLOWED_TZ = {"America/Sao_Paulo", "Europe/Berlin", "UTC"}


async def world_or_404(name: str) -> dict:
    found = await query("SELECT id, name, location, pvp_type, battleye_protected, transfer_type, players_online, "
                        "updated_at FROM worlds WHERE lower(name) = lower(%s)", name)
    if not found:
        raise HTTPException(404, "mundo não encontrado")
    return found[0]


@app.get("/v1/overview")
async def overview(response: Response):
    series = await query(
        """
        SELECT ts, sum(players_online)::int AS players_online FROM world_online_5m
        WHERE ts > now() - interval '48 hours' GROUP BY ts ORDER BY ts
        """
    )
    regions = await query(
        "SELECT location, count(*)::int AS worlds, sum(players_online)::int AS players_online "
        "FROM worlds GROUP BY location ORDER BY players_online DESC"
    )
    cache(response, 60)
    return {"series_48h": series, "regions": regions}


@app.get("/v1/worlds/{name}/health")
async def world_health(name: str, response: Response, days: int = 14):
    days = max(1, min(days, 90))
    w = await world_or_404(name)
    hourly = await query(
        """
        SELECT date_trunc('hour', ts) AS hour, round(avg(players_online))::int AS avg, max(players_online) AS max
        FROM world_online_5m WHERE world_id = %s AND ts > now() - make_interval(days => %s)
        GROUP BY 1 ORDER BY 1
        """,
        w["id"], days,
    )
    record = await query(
        "SELECT ts, players_online FROM world_online_5m WHERE world_id = %s ORDER BY players_online DESC, ts LIMIT 1",
        w["id"],
    )
    transfers = await query(
        """
        SELECT count(*) FILTER (WHERE to_world_id = %s)::int AS arrived,
               count(*) FILTER (WHERE from_world_id = %s)::int AS left
        FROM transfers WHERE detected_day > current_date - %s
        """,
        w["id"], w["id"], days,
    )
    since = await query("SELECT min(ts) AS since FROM world_online_5m WHERE world_id = %s", w["id"])
    cache(response, 300)
    return {"world": w["name"], "days": days, "hourly": hourly, "record": record[0] if record else None,
            "transfers": transfers[0], "collecting_since": since[0]["since"]}


@app.get("/v1/worlds/{name}/heatmap")
async def world_heatmap(name: str, response: Response, vocation: str | None = None, band: str | None = None,
                        tz: str = "America/Sao_Paulo", weeks: int = 4):
    """Média de jogadores online por dia da semana × hora. Só agregado: célula com média < 5
    some quando há filtro (k-anonimato), para não expor grupos pequenos."""
    if tz not in ALLOWED_TZ:
        raise HTTPException(422, "fuso não suportado")
    if vocation and vocation not in VOCATION_GROUPS:
        raise HTTPException(422, "vocação inválida")
    if band and band not in BANDS:
        raise HTTPException(422, "faixa inválida")
    weeks = max(1, min(weeks, 12))
    w = await world_or_404(name)
    vocs = VOCATION_GROUPS[vocation] if vocation else None
    rows = await query(
        """
        WITH per_hour AS (
          SELECT s.hour, s.snapshots,
                 coalesce(sum(b.samples) FILTER (WHERE (%s::text[] IS NULL OR b.vocation = ANY(%s::text[]))
                                                   AND (%s::text IS NULL OR b.level_band = %s::text)), 0) AS samples
          FROM world_hour_snapshots s
          LEFT JOIN activity_buckets b ON b.world_id = s.world_id AND b.hour = s.hour
          WHERE s.world_id = %s AND s.hour > now() - make_interval(weeks => %s)
          GROUP BY s.hour, s.snapshots
        )
        SELECT extract(isodow FROM hour AT TIME ZONE %s)::int AS dow,
               extract(hour FROM hour AT TIME ZONE %s)::int AS hod,
               round(avg(samples::numeric / snapshots), 1)::float AS avg,
               count(*)::int AS hours
        FROM per_hour GROUP BY 1, 2 ORDER BY 1, 2
        """,
        vocs, vocs, band, band, w["id"], weeks, tz, tz,
    )
    filtered = bool(vocation or band)
    cells = [{**r, "avg": (None if filtered and r["avg"] < MIN_CELL else r["avg"])} for r in rows]
    cache(response, 600)
    return {"world": w["name"], "tz": tz, "weeks": weeks, "vocation": vocation, "band": band,
            "min_cell": MIN_CELL, "cells": cells}


@app.get("/v1/worlds/{name}/towns/{town}")
async def world_town(name: str, town: str, response: Response):
    w = await world_or_404(name)
    rows = await query(
        """
        SELECT h.house_id, h.name, h.kind, h.size, h.rent, h.beds,
               s.rented, s.auctioned, s.current_bid, s.time_left, s.snap_day,
               o.owner
        FROM houses h
        LEFT JOIN LATERAL (SELECT * FROM house_snapshots s WHERE s.world_id = h.world_id AND s.house_id = h.house_id
                           ORDER BY snap_day DESC LIMIT 1) s ON true
        LEFT JOIN house_owners o ON o.world_id = h.world_id AND o.house_id = h.house_id AND o.ended_day IS NULL
        WHERE h.world_id = %s AND lower(h.town) = lower(%s)
        ORDER BY h.kind, h.name
        """,
        w["id"], town,
    )
    if not rows:
        raise HTTPException(404, "cidade sem casas registradas")
    cache(response, 600)
    return {"world": w["name"], "town": town, "houses": rows}


@app.get("/v1/worlds/{name}/houses/{house_id}")
async def world_house(name: str, house_id: int, response: Response):
    w = await world_or_404(name)
    found = await query(
        "SELECT house_id, town, name, kind, size, rent, beds, details_fetched_at FROM houses "
        "WHERE world_id = %s AND house_id = %s",
        w["id"], house_id,
    )
    if not found:
        raise HTTPException(404, "casa não encontrada")
    history = await query(
        "SELECT snap_day, rented, auctioned, current_bid, time_left FROM house_snapshots "
        "WHERE world_id = %s AND house_id = %s ORDER BY snap_day DESC LIMIT 60",
        w["id"], house_id,
    )
    owners = await query(
        "SELECT owner, first_seen_day, last_seen_day, ended_day FROM house_owners "
        "WHERE world_id = %s AND house_id = %s ORDER BY first_seen_day DESC",
        w["id"], house_id,
    )
    cache(response, 600)
    return {"world": w["name"], **found[0], "history": history, "owners": owners}


@app.get("/v1/worlds/{name}/guilds/{guild}")
async def world_guild(name: str, guild: str, response: Response):
    """Dados públicos da guild (os mesmos do tibia.com). Sem status online/offline dos membros."""
    w = await world_or_404(name)
    found = await query(
        "SELECT id, name, in_formation, logo_url, founded, members_total, in_war, open_applications, guildhalls, "
        "first_seen_day, disbanded_day, details_fetched_at FROM guilds WHERE world_id = %s AND lower(name) = lower(%s)",
        w["id"], guild,
    )
    if not found:
        raise HTTPException(404, "guild não encontrada")
    g = found[0]
    gid = g.pop("id")
    members = await query(
        "SELECT name, rank, title, vocation, level, joined FROM guild_members WHERE guild_id = %s "
        "ORDER BY level DESC NULLS LAST, name",
        gid,
    )
    events = await query(
        "SELECT name, event, event_day FROM guild_events WHERE guild_id = %s ORDER BY event_day DESC, name LIMIT 100",
        gid,
    )
    vocations: dict[str, int] = {}
    for m in members:
        base = next((k for k, v in VOCATION_GROUPS.items() if m["vocation"] in v), "none")
        vocations[base] = vocations.get(base, 0) + 1
    cache(response, 600)
    return {"world": w["name"], **g, "members": members, "events": events, "vocations": vocations}
