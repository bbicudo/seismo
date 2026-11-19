"""API do Seismo: status do coletor, mundos, agregados anônimos, dados públicos de guilds e casas
e o fluxo de opt-out. Quem fez opt-out não aparece em nenhuma rota."""

import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
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
        return await cur.fetchall() if cur.description else []  # INSERT/UPDATE não devolvem linhas


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
    # mortes de jogadores para criaturas no último dia fechado (as kill statistics não contam PvP)
    top_deaths = await query(
        """
        SELECT w.name, k.stats_day, sum(k.players_killed)::int AS deaths, sum(k.killed)::int AS creatures_killed
        FROM kill_stats_daily k JOIN worlds w ON w.id = k.world_id
        WHERE k.stats_day = (SELECT max(stats_day) FROM kill_stats_daily)
        GROUP BY w.name, k.stats_day ORDER BY deaths DESC, w.name LIMIT 10
        """
    )
    cache(response, 60)
    return {"series_48h": series, "regions": regions, "top_deaths": top_deaths}


# Personagens novos (estimativa): vistos online pela primeira vez já em level baixo (até 7), depois do
# primeiro dia de coleta daquele mundo (no primeiro dia todo mundo é "visto pela primeira vez").
NEW_LEVEL_MAX = 7
NEW_CHARS_SQL = f"""
    WITH starts AS (SELECT world_id, min(first_seen_day) AS start_day FROM characters GROUP BY world_id)
    SELECT w.name, count(c.id)::int AS new_characters
    FROM worlds w
    JOIN starts s ON s.world_id = w.id
    JOIN characters c ON c.world_id = w.id
    WHERE c.first_level <= {NEW_LEVEL_MAX}
      AND c.first_seen_day > s.start_day
      AND c.first_seen_day > current_date - %s
      AND (%s::int IS NULL OR w.id = %s::int)
    GROUP BY w.name
"""


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
    new_chars = await query(NEW_CHARS_SQL, days, w["id"], w["id"])
    new_by_day = await query(
        f"""
        WITH s AS (SELECT min(first_seen_day) AS start_day FROM characters WHERE world_id = %s)
        SELECT c.first_seen_day AS day, count(*)::int AS new_characters,
               count(*) FILTER (WHERE c.vocation = 'None')::int AS without_vocation
        FROM characters c, s
        WHERE c.world_id = %s AND c.first_level <= {NEW_LEVEL_MAX}
          AND c.first_seen_day > s.start_day AND c.first_seen_day > current_date - %s
        GROUP BY c.first_seen_day ORDER BY c.first_seen_day DESC
        """,
        w["id"], w["id"], days,
    )
    deaths = await query(
        """
        SELECT stats_day, sum(players_killed)::int AS deaths FROM kill_stats_daily
        WHERE world_id = %s AND stats_day > current_date - %s GROUP BY stats_day ORDER BY stats_day
        """,
        w["id"], days,
    )
    cache(response, 300)
    return {"world": w["name"], "days": days, "hourly": hourly, "record": record[0] if record else None,
            "transfers": transfers[0], "collecting_since": since[0]["since"],
            "new_characters": new_chars[0]["new_characters"] if new_chars else 0,
            "new_level_max": NEW_LEVEL_MAX, "new_characters_by_day": new_by_day, "deaths_by_day": deaths}


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
             AND NOT EXISTS (SELECT 1 FROM privacy_optouts p WHERE lower(p.name) = lower(o.owner))
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
        "SELECT owner, first_seen_day, last_seen_day, ended_day FROM house_owners o "
        "WHERE world_id = %s AND house_id = %s "
        "AND NOT EXISTS (SELECT 1 FROM privacy_optouts p WHERE lower(p.name) = lower(o.owner)) "
        "ORDER BY first_seen_day DESC",
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
        "SELECT name, rank, title, vocation, level, joined FROM guild_members m WHERE guild_id = %s "
        "AND NOT EXISTS (SELECT 1 FROM privacy_optouts p WHERE lower(p.name) = lower(m.name)) "
        "ORDER BY level DESC NULLS LAST, name",
        gid,
    )
    events = await query(
        "SELECT name, event, event_day FROM guild_events e WHERE guild_id = %s "
        "AND NOT EXISTS (SELECT 1 FROM privacy_optouts p WHERE lower(p.name) = lower(e.name)) "
        "ORDER BY event_day DESC, name LIMIT 100",
        gid,
    )
    vocations: dict[str, int] = {}
    for m in members:
        base = next((k for k, v in VOCATION_GROUPS.items() if m["vocation"] in v), "none")
        vocations[base] = vocations.get(base, 0) + 1
    cache(response, 600)
    return {"world": w["name"], **g, "members": members, "events": events, "vocations": vocations}


# ---------------------------------------------------------------- opt-out
# 1) o dono pede o opt-out e recebe um código; 2) cola o código no comentário do personagem no tibia.com;
# 3) pede a verificação: a API põe o pedido numa fila e o coletor (que tem acesso à internet) confere o
# comentário pela TibiaData. Confirmado, o personagem some do site e os dados ligados ao nome são apagados.

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z' -]{1,28}[A-Za-z]$")
OPTOUT_TTL = timedelta(hours=48)
VERIFY_COOLDOWN = timedelta(minutes=2)
OPTOUT_QUEUE = "seismo:optout:queue"


class OptoutIn(BaseModel):
    name: str


def clean_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not NAME_RE.match(name):
        raise HTTPException(422, "nome de personagem inválido")
    return name


async def optout_state(name: str) -> dict:
    done = await query("SELECT name, created_at FROM privacy_optouts WHERE lower(name) = lower(%s)", name)
    if done:
        return {"name": done[0]["name"], "status": "verified", "since": done[0]["created_at"]}
    req = await query(
        "SELECT name, code, status, message, expires_at, checked_at FROM optout_requests "
        "WHERE lower(name) = lower(%s) ORDER BY created_at DESC LIMIT 1",
        name,
    )
    if not req:
        return {"name": name, "status": "none"}
    r = req[0]
    if r["status"] in ("pending", "failed") and r["expires_at"] < datetime.now(timezone.utc):
        return {"name": name, "status": "expired"}
    return r


@app.get("/v1/optout")
async def optout_status(name: str, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return await optout_state(clean_name(name))


@app.post("/v1/optout/request")
async def optout_request(body: OptoutIn, response: Response):
    response.headers["Cache-Control"] = "no-store"
    name = clean_name(body.name)
    state = await optout_state(name)
    if state["status"] in ("verified", "pending", "checking", "failed"):
        return state  # já existe um código válido (ou o opt-out já foi feito)
    code = f"seismo-{secrets.token_hex(3)}"
    await query(
        "INSERT INTO optout_requests (name, code, expires_at) VALUES (%s, %s, %s)",
        name, code, datetime.now(timezone.utc) + OPTOUT_TTL,
    )
    return await optout_state(name)


@app.post("/v1/optout/verify")
async def optout_verify(body: OptoutIn, response: Response):
    response.headers["Cache-Control"] = "no-store"
    name = clean_name(body.name)
    state = await optout_state(name)
    if state["status"] not in ("pending", "failed"):
        return state
    checked = state.get("checked_at")
    if checked and datetime.now(timezone.utc) - checked < VERIFY_COOLDOWN:
        return {**state, "message": "aguarde 2 minutos entre verificações"}
    await query(
        "UPDATE optout_requests SET status = 'checking', message = NULL, checked_at = now() "
        "WHERE id = (SELECT id FROM optout_requests WHERE lower(name) = lower(%s) ORDER BY created_at DESC LIMIT 1)",
        name,
    )
    await app.state.redis.rpush(OPTOUT_QUEUE, name)
    return await optout_state(name)
