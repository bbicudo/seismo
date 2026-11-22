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
from .flags import DEFAULTS, FLAGS
from .params import BY_KEY, DEFAULTS as PARAM_DEFAULTS, PARAMS, validate
from .settings import Settings

settings = Settings()


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
              default_response_class=ORJSONResponse)  # prefixo /api: --root-path do uvicorn (Dockerfile)


async def query(sql: str, *params) -> list[dict]:
    async with app.state.pool.connection() as conn:
        cur = await conn.execute(sql, params)
        return await cur.fetchall() if cur.description else []  # INSERT/UPDATE não devolvem linhas


_flags_cache: dict = {"at": 0.0, "values": dict(DEFAULTS)}


async def flags() -> dict[str, bool]:
    """Estado das feature flags (cache de 10 s). Sem linha na tabela, vale o padrão (ligado)."""
    import time
    if time.monotonic() - _flags_cache["at"] > 10:
        rows = await query("SELECT key, enabled FROM feature_flags")
        _flags_cache["values"] = {**DEFAULTS, **{r["key"]: r["enabled"] for r in rows if r["key"] in DEFAULTS}}
        _flags_cache["at"] = time.monotonic()
    return _flags_cache["values"]


PARAM: dict = dict(PARAM_DEFAULTS)
_params_cache: dict = {"at": 0.0}


async def params() -> dict:
    """Parâmetros ajustados no /admin (cache de 10 s). Atualiza o dicionário PARAM usado pelas rotas."""
    import time
    if time.monotonic() - _params_cache["at"] > 10:
        rows = await query("SELECT key, value FROM app_settings")
        fresh = dict(PARAM_DEFAULTS)
        for r in rows:
            if r["key"] in BY_KEY:
                try:
                    fresh[r["key"]] = validate(r["key"], r["value"])
                except (ValueError, TypeError):
                    pass
        PARAM.clear()
        PARAM.update(fresh)
        _params_cache["at"] = time.monotonic()
    return PARAM


async def require(flag: str) -> None:
    if not (await flags()).get(flag, True):
        raise HTTPException(404, "recurso desligado")


def cache(response: Response, seconds: int) -> None:
    response.headers["Cache-Control"] = f"public, max-age={seconds}"


@app.get("/healthz")
async def healthz():
    await query("SELECT 1")
    await app.state.redis.ping()
    return {"ok": True}


@app.get("/v1/status")
async def status(response: Response):
    """Status público: só existe se a flag page_status estiver ligada (padrão: desligada no beta)."""
    await require("page_status")
    return await status_payload(response)


@app.get("/v1/admin/status")
async def admin_status(response: Response):
    """Mesmo conteúdo, só para a área administrativa (a rota não sai pelo Caddy)."""
    return await status_payload(response)


async def status_payload(response: Response):
    r = app.state.redis
    day = datetime.now(timezone.utc).date().isoformat()
    keys = ["seismo:paused", "seismo:last_cycle_at", "seismo:last_cycle_seconds", "seismo:last_cycle_worlds",
            f"seismo:requests:{day}", f"seismo:errors:{day}", "seismo:request_cap", "seismo:budget_left"]
    paused, last_at, last_s, last_w, reqs, errs, cap, left = await r.mget(keys)
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
    errors_by = await r.hgetall(f"seismo:errors_by:{day}")
    errors = sorted(({"kind": k.split("|")[0], "reason": k.split("|")[-1], "n": int(v)} for k, v in errors_by.items()),
                    key=lambda e: -e["n"])
    cache(response, 15)
    return {
        "env": settings.seismo_env,
        "errors_by": errors,
        "daily_jobs": jobs,
        "progress": progress,
        "collector": {
            "paused": paused == "1",
            "last_cycle_at": last_at,
            "last_cycle_seconds": float(last_s) if last_s else None,
            "last_cycle_worlds": last_w,
            "requests_today_utc": int(reqs or 0),
            "errors_today_utc": int(errs or 0),
            "request_cap": int(cap) if cap else None,
            "budget_left": int(left) if left else None,
        },
        "database": counts,
    }


@app.get("/v1/worlds")
async def worlds(response: Response):
    rows = await query(
        """
        SELECT name, location, pvp_type, battleye_protected, battleye_type, transfer_type, players_online, updated_at
        FROM worlds ORDER BY players_online DESC, name
        """
    )
    cache(response, 60)
    return rows


@app.get("/v1/worlds/{name}")
async def world(name: str, response: Response):
    await params()
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
        {"vocation": voc, "level_band": band, "players": n if n >= PARAM["min_cell"] else None}
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
    return {**w, "series_48h": series, "online_now": len(online), "composition": composition, "min_cell": PARAM["min_cell"],
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
    await params()
    found = await query("SELECT id, name, location, pvp_type, battleye_protected, battleye_type, transfer_type, players_online, "
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
NEW_CHARS_SQL = f"""
    WITH starts AS (SELECT world_id, min(first_seen_day) AS start_day FROM characters GROUP BY world_id)
    SELECT w.name, count(c.id)::int AS new_characters
    FROM worlds w
    JOIN starts s ON s.world_id = w.id
    JOIN characters c ON c.world_id = w.id
    WHERE c.first_level <= %s
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
    event_days = await query(
        "SELECT day, string_agg(name, ', ' ORDER BY name) AS names FROM game_events "
        "WHERE kind IN ('double_xp', 'double_skill', 'rapid_respawn') AND day > current_date - %s GROUP BY day ORDER BY day",
        days,
    )
    new_chars = await query(NEW_CHARS_SQL, PARAM["new_level_max"], days, w["id"], w["id"])
    new_by_day = await query(
        f"""
        WITH s AS (SELECT min(first_seen_day) AS start_day FROM characters WHERE world_id = %s)
        SELECT c.first_seen_day AS day, count(*)::int AS new_characters,
               count(*) FILTER (WHERE c.vocation = 'None')::int AS without_vocation
        FROM characters c, s
        WHERE c.world_id = %s AND c.first_level <= %s
          AND c.first_seen_day > s.start_day AND c.first_seen_day > current_date - %s
        GROUP BY c.first_seen_day ORDER BY c.first_seen_day DESC
        """,
        w["id"], w["id"], PARAM["new_level_max"], days,
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
            "new_level_max": PARAM["new_level_max"], "new_characters_by_day": new_by_day, "deaths_by_day": deaths,
            "event_days": event_days}


@app.get("/v1/worlds/{name}/heatmap")
async def world_heatmap(name: str, response: Response, vocation: str | None = None, band: str | None = None,
                        tz: str = "America/Sao_Paulo", weeks: int = 4, events: str = "exclude"):
    """Média de jogadores online por dia da semana × hora. Só agregado: célula com média < 5
    some quando há filtro (k-anonimato), para não expor grupos pequenos.
    events: exclude (padrão, ignora dias de double/rapid respawn) | only | include."""
    if events not in ("exclude", "only", "include"):
        raise HTTPException(422, "events deve ser exclude, only ou include")
    await require("page_heatmap")
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
            AND (%s = 'include' OR (EXISTS (
                  SELECT 1 FROM game_events e WHERE e.kind IN ('double_xp', 'rapid_respawn')
                  AND e.day = ((s.hour AT TIME ZONE 'Europe/Berlin') - interval '10 hours')::date)) = (%s = 'only'))
          GROUP BY s.hour, s.snapshots
        )
        SELECT extract(isodow FROM hour AT TIME ZONE %s)::int AS dow,
               extract(hour FROM hour AT TIME ZONE %s)::int AS hod,
               round(avg(samples::numeric / snapshots), 1)::float AS avg,
               count(*)::int AS hours
        FROM per_hour GROUP BY 1, 2 ORDER BY 1, 2
        """,
        vocs, vocs, band, band, w["id"], weeks, events, events, tz, tz,
    )
    filtered = bool(vocation or band)
    cells = [{**r, "avg": (None if filtered and r["avg"] < PARAM["min_cell"] else r["avg"])} for r in rows]
    cache(response, 600)
    return {"world": w["name"], "tz": tz, "weeks": weeks, "vocation": vocation, "band": band, "events": events,
            "min_cell": PARAM["min_cell"], "cells": cells}


@app.get("/v1/worlds/{name}/guilds/{guild}/heatmap")
async def guild_heatmap(name: str, guild: str, response: Response, tz: str = "America/Sao_Paulo",
                        weeks: int = 4, events: str = "exclude"):
    """Quando os membros da guild jogam: média de membros online por dia da semana e hora. Só para guilds
    grandes e só agregado; célula com média abaixo do tamanho mínimo de grupo fica vazia."""
    await require("page_heatmap")
    await require("page_guilds")
    if tz not in ALLOWED_TZ:
        raise HTTPException(422, "fuso não suportado")
    if events not in ("exclude", "only", "include"):
        raise HTTPException(422, "events deve ser exclude, only ou include")
    weeks = max(1, min(weeks, 12))
    w = await world_or_404(name)
    found = await query("SELECT id, name, members_total FROM guilds WHERE world_id = %s AND lower(name) = lower(%s)",
                        w["id"], guild)
    if not found:
        raise HTTPException(404, "guild não encontrada")
    g = found[0]
    min_members, min_cell = PARAM["guild_heatmap_min_members"], PARAM["min_cell"]
    base = {"world": w["name"], "guild": g["name"], "tz": tz, "weeks": weeks, "events": events,
            "min_members": min_members, "min_cell": min_cell}
    if (g["members_total"] or 0) < min_members:
        cache(response, 600)
        return {**base, "eligible": False, "cells": []}
    rows = await query(
        """
        WITH per_hour AS (
          SELECT s.hour, s.snapshots, coalesce(b.samples, 0) AS samples
          FROM world_hour_snapshots s
          LEFT JOIN guild_activity_buckets b ON b.guild_id = %s AND b.hour = s.hour
          WHERE s.world_id = %s AND s.hour > now() - make_interval(weeks => %s)
            -- só horas completas desde que a contagem por guild começou (antes disso não havia dado, não zero)
            AND s.hour > (SELECT min(hour) FROM guild_activity_buckets)
            AND s.hour < date_trunc('hour', now())
            AND (%s = 'include' OR (EXISTS (
                  SELECT 1 FROM game_events e WHERE e.kind IN ('double_xp', 'rapid_respawn')
                  AND e.day = ((s.hour AT TIME ZONE 'Europe/Berlin') - interval '10 hours')::date)) = (%s = 'only'))
        )
        SELECT extract(isodow FROM hour AT TIME ZONE %s)::int AS dow,
               extract(hour FROM hour AT TIME ZONE %s)::int AS hod,
               round(avg(samples::numeric / snapshots), 1)::float AS avg
        FROM per_hour GROUP BY 1, 2 ORDER BY 1, 2
        """,
        g["id"], w["id"], weeks, events, events, tz, tz,
    )
    cells = [{**r, "avg": None if r["avg"] < min_cell else r["avg"]} for r in rows]
    cache(response, 600)
    return {**base, "eligible": True, "cells": cells}


@app.get("/v1/worlds/{name}/towns/{town}")
async def world_town(name: str, town: str, response: Response):
    await require("page_houses")
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
    await require("page_houses")
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
    await require("page_guilds")
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


# ---------------------------------------------------------------- eventos e destaques do dia

@app.get("/v1/events")
async def game_events(response: Response, past: int = 30, ahead: int = 30):
    await require("page_events")
    past, ahead = max(0, min(past, 365)), max(0, min(ahead, 60))
    today = (await query("SELECT ((now() AT TIME ZONE 'Europe/Berlin') - interval '10 hours')::date AS d"))[0]["d"]
    rows = await query(
        "SELECT day, name, kind, source, url FROM game_events WHERE day BETWEEN %s AND %s ORDER BY day, name",
        today - timedelta(days=past), today + timedelta(days=ahead),
    )
    boosted = await query("SELECT day, creature, boss FROM daily_boosted ORDER BY day DESC LIMIT 1")
    cache(response, 600)
    return {"today": today, "boosted": boosted[0] if boosted else None,
            "active": [r for r in rows if r["day"] == today], "events": rows}


# ---------------------------------------------------------------- raids e termômetro



@app.get("/v1/worlds/{name}/raids")
async def world_raids(name: str, response: Response, days: int = 90):
    await require("page_raids")
    days = max(7, min(days, 365))
    w = await world_or_404(name)
    rows = await query(
        """
        SELECT r.slug, r.name, r.region, o.day, o.kills
        FROM raid_occurrences o JOIN raids r ON r.id = o.raid_id
        WHERE o.world_id = %s AND o.day > current_date - %s
        ORDER BY o.day DESC, r.name
        """,
        w["id"], days,
    )
    by_raid: dict[str, dict] = {}
    for r in rows:
        b = by_raid.setdefault(r["slug"], {"slug": r["slug"], "name": r["name"], "region": r["region"], "days": []})
        b["days"].append(r["day"])
    summary = []
    for b in by_raid.values():
        ds = sorted(set(b["days"]))
        gaps = sorted((ds[i] - ds[i - 1]).days for i in range(1, len(ds)))
        item = {"slug": b["slug"], "name": b["name"], "region": b["region"], "count": len(ds), "last": ds[-1],
                "median_gap_days": None, "next_from": None, "next_to": None}
        if len(gaps) >= 2:  # 3 ocorrências ou mais: dá para estimar uma janela (nunca uma data certa)
            med = gaps[len(gaps) // 2]
            q1, q3 = gaps[len(gaps) // 4], gaps[(3 * len(gaps)) // 4]
            item.update(median_gap_days=med, next_from=ds[-1] + timedelta(days=max(1, q1)),
                        next_to=ds[-1] + timedelta(days=max(q1 + 1, q3)))
        summary.append(item)
    summary.sort(key=lambda s: s["last"], reverse=True)
    meta = (await query(
        "SELECT count(*) FILTER (WHERE cardinality(signature) > 0)::int AS detectable, count(*)::int AS total, "
        "(SELECT count(DISTINCT stats_day)::int FROM kill_stats_daily WHERE world_id = %s) AS history_days FROM raids",
        w["id"],
    ))[0]
    cache(response, 900)
    return {"world": w["name"], "days": days, "recent": rows[:50], "raids": summary, **meta}


@app.get("/v1/worlds/{name}/thermometer")
async def world_thermometer(name: str, response: Response):
    """Criaturas com mortes muito acima (em alta) ou abaixo (em queda, spot provavelmente livre) do normal,
    comparando o último dia com a média dos 28 dias anteriores do mesmo mundo (z-score)."""
    await require("page_raids")
    w = await world_or_404(name)
    rows = await query(
        """
        WITH last AS (SELECT max(stats_day) AS d FROM kill_stats_daily WHERE world_id = %s),
        hist AS (
          SELECT k.race, avg(k.killed) AS mu, stddev_samp(k.killed) AS sd, count(*) AS n
          FROM kill_stats_daily k, last
          WHERE k.world_id = %s AND k.stats_day < last.d AND k.stats_day >= last.d - 28
            AND k.stats_day NOT IN (SELECT day FROM game_events WHERE kind IN ('double_xp', 'rapid_respawn'))
          GROUP BY k.race
        ),
        today AS (SELECT k.race, k.killed FROM kill_stats_daily k, last WHERE k.world_id = %s AND k.stats_day = last.d)
        SELECT h.race, coalesce(t.killed, 0) AS killed, round(h.mu)::int AS average, h.n::int AS days,
               round(((coalesce(t.killed, 0) - h.mu) / nullif(h.sd, 0))::numeric, 1)::float AS z,
               (SELECT d FROM last) AS day,
               EXISTS (SELECT 1 FROM daily_boosted b, last
                       WHERE b.day = last.d AND lower(h.race) IN (lower(b.creature), lower(b.creature) || 's',
                                                                    lower(b.creature) || 'es', lower(b.boss))) AS boosted
        FROM hist h LEFT JOIN today t ON t.race = h.race
        WHERE h.n >= %s AND h.mu >= %s AND h.sd > 0
        """,
        w["id"], w["id"], w["id"], PARAM["thermo_min_days"], PARAM["thermo_min_avg"],
    )
    hot = sorted((r for r in rows if r["z"] is not None and r["z"] >= PARAM["thermo_z"]), key=lambda r: -r["z"])[:12]
    cold = sorted((r for r in rows if r["z"] is not None and r["z"] <= -PARAM["thermo_z"]), key=lambda r: r["z"])[:12]
    history = (await query("SELECT count(DISTINCT stats_day)::int AS n FROM kill_stats_daily WHERE world_id = %s",
                           w["id"]))[0]["n"]
    day = rows[0]["day"] if rows else None
    day_events = await query("SELECT name, kind FROM game_events WHERE day = %s ORDER BY name", day) if day else []
    cache(response, 900)
    return {"world": w["name"], "day": day, "history_days": history, "min_days": PARAM["thermo_min_days"] + 1,
            "hot": hot, "cold": cold, "day_events": day_events}


# ---------------------------------------------------------------- sitemap
# Lista as páginas públicas para o sitemap do site. Perfis de personagem e casas ficam de fora de propósito:
# são páginas sobre pessoas ou muito numerosas, e não precisam ser oferecidas aos buscadores.


@app.get("/v1/sitemap")
async def sitemap_data(response: Response):
    f = await flags()
    worlds = await query("SELECT name, updated_at FROM worlds ORDER BY name")
    guilds = await query(
        "SELECT g.name, w.name AS world, g.details_fetched_at AS updated_at FROM guilds g JOIN worlds w ON w.id = g.world_id "
        "WHERE g.disbanded_day IS NULL ORDER BY w.name, g.name"
    ) if f.get("page_guilds", True) else []
    towns = await query(
        "SELECT DISTINCT w.name AS world, h.town FROM houses h JOIN worlds w ON w.id = h.world_id ORDER BY 1, 2"
    ) if f.get("page_houses", True) else []
    response.headers["Cache-Control"] = "public, max-age=3600"
    return {"flags": f, "worlds": worlds, "guilds": guilds, "towns": towns}


# ---------------------------------------------------------------- personagem
# Mostra só o que a política de privacidade prevê: totais de minutos por dia de jogo (nunca horários),
# level por mês, guild, casas e transfers. Quem fez opt-out não tem página.


@app.get("/v1/characters/{name}")
async def character(name: str, response: Response, days: int = 60):
    await require("page_characters")
    await params()
    days = max(7, min(days, 400))
    found = await query(
        f"""
        SELECT c.id, c.name, c.level, c.vocation, c.first_seen_day, c.last_seen_day, w.name AS world, w.location, w.pvp_type
        FROM characters c JOIN worlds w ON w.id = c.world_id
        WHERE lower(c.name) = lower(%s) AND {NOT_OPTED.format(col='c.name')}
        """,
        name,
    )
    if not found:
        # membro de guild que o Seismo ainda não viu online: perfil mínimo com os dados públicos da guild
        found = await query(
            f"""
            SELECT NULL::bigint AS id, m.name, m.level, m.vocation, NULL::date AS first_seen_day, NULL::date AS last_seen_day,
                   w.name AS world, w.location, w.pvp_type
            FROM guild_members m JOIN guilds g ON g.id = m.guild_id JOIN worlds w ON w.id = g.world_id
            WHERE lower(m.name) = lower(%s) AND {NOT_OPTED.format(col='m.name')} LIMIT 1
            """,
            name,
        )
        if not found:
            raise HTTPException(404, "personagem não encontrado")
    c = found[0]
    cid = c.pop("id") or 0
    daily = await query(
        "SELECT game_day AS day, minutes FROM daily_online WHERE character_id = %s AND game_day > current_date - %s "
        "ORDER BY game_day",
        cid, days,
    )
    months = await query(
        "SELECT month, level_start, level_end FROM monthly_level WHERE character_id = %s ORDER BY month DESC LIMIT 24",
        cid,
    )
    guild = await query(
        "SELECT g.name, m.rank, m.title, m.joined, w.name AS world FROM guild_members m "
        "JOIN guilds g ON g.id = m.guild_id JOIN worlds w ON w.id = g.world_id "
        "WHERE lower(m.name) = lower(%s) AND g.disbanded_day IS NULL LIMIT 1",
        c["name"],
    )
    houses = await query(
        "SELECT h.house_id, h.name, h.town, h.kind, w.name AS world, o.first_seen_day "
        "FROM house_owners o JOIN houses h ON h.world_id = o.world_id AND h.house_id = o.house_id "
        "JOIN worlds w ON w.id = o.world_id WHERE lower(o.owner) = lower(%s) AND o.ended_day IS NULL ORDER BY h.name",
        c["name"],
    )
    transfers = await query(
        "SELECT t.detected_day AS day, wf.name AS from_world, wt.name AS to_world FROM transfers t "
        "JOIN worlds wf ON wf.id = t.from_world_id JOIN worlds wt ON wt.id = t.to_world_id "
        "WHERE t.character_id = %s ORDER BY t.detected_day DESC LIMIT 20",
        cid,
    )
    last30 = [d for d in daily if (datetime.now(timezone.utc).date() - d["day"]).days < 30]
    cache(response, 300)
    return {
        **c, "seen_online": cid != 0, "days": days, "daily": daily, "months": months,
        "guild": guild[0] if guild else None, "houses": houses, "transfers": transfers,
        "minutes_30d": sum(d["minutes"] for d in last30), "active_days_30d": len(last30),
    }


@app.get("/v1/characters")
async def character_search(q: str, response: Response):
    """Busca por começo do nome (mínimo 3 letras), para a caixa de busca do site."""
    await require("page_characters")
    term = " ".join(q.split())
    if len(term) < 3:
        return []
    rows = await query(
        f"""
        SELECT c.name, c.level, c.vocation, w.name AS world FROM characters c JOIN worlds w ON w.id = c.world_id
        WHERE lower(c.name) LIKE lower(%s) || '%%' AND {NOT_OPTED.format(col='c.name')}
        ORDER BY (lower(c.name) = lower(%s)) DESC, c.level DESC LIMIT 10
        """,
        term, term,
    )
    cache(response, 60)
    return rows


# ---------------------------------------------------------------- mapa de hunts
# As kill statistics dizem quantas criaturas de cada tipo morreram no mundo, não onde. Cada hunt da TibiaWiki
# lista as criaturas que vivem lá: as mortes de uma criatura são divididas igualmente entre as hunts onde ela
# vive. É uma estimativa de onde se caçou mais, não uma medição de posição de jogadores.

MAP_BOUNDS = {"x_min": 31744, "y_min": 30976, "width": 2560, "height": 2048}


@app.get("/v1/worlds/{name}/hunts")
async def world_hunts(name: str, response: Response, day: str | None = None):
    await require("page_hunts")
    w = await world_or_404(name)
    days = await query(
        "SELECT DISTINCT stats_day FROM kill_stats_daily WHERE world_id = %s ORDER BY stats_day DESC LIMIT 30", w["id"],
    )
    available = [d["stats_day"] for d in days]
    if not available:
        return {"world": w["name"], "day": None, "days": [], "hunts": [], "bounds": MAP_BOUNDS, "creatures": [],
                "totals": {"killed": None, "deaths": None}, "trends": False}
    chosen = available[0]
    if day:
        try:
            wanted = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(422, "dia inválido (use AAAA-MM-DD)")
        if wanted not in available:
            raise HTTPException(404, "sem kill statistics nesse dia")
        chosen = wanted
    trend_days = PARAM["hunt_trend_days"]
    rows = await query(
        """
        WITH hk AS (SELECT DISTINCT h.slug, k AS key FROM hunts h, unnest(h.race_keys) k),
        share AS (SELECT key, count(*) AS n FROM hk GROUP BY key),
        kills AS (SELECT stats_day, lower(race) AS race, race AS label, killed, players_killed FROM kill_stats_daily
                  WHERE world_id = %s AND stats_day BETWEEN %s::date - %s AND %s::date
                    AND (killed > 0 OR players_killed > 0)),
        per AS (
          SELECT hk.slug, kills.stats_day, kills.label, kills.killed::float / share.n AS part,
                 kills.players_killed::float / share.n AS pk
          FROM hk JOIN share ON share.key = hk.key JOIN kills ON kills.race = hk.key
        ),
        agg AS (
          SELECT slug, sum(part) FILTER (WHERE stats_day = %s) AS kills, sum(pk) FILTER (WHERE stats_day = %s) AS deaths,
                 sum(part) FILTER (WHERE stats_day < %s) AS base_kills
          FROM per GROUP BY slug
        )
        SELECT h.slug, h.name, h.city, h.x, h.y, h.z, round(agg.kills)::int AS kills,
               round(coalesce(agg.deaths, 0))::int AS deaths, coalesce(agg.base_kills, 0)::float AS base_kills,
               (SELECT json_agg(t ORDER BY t.part DESC) FROM (
                  SELECT p2.label AS creature, round(p2.part)::int AS part FROM per p2
                  WHERE p2.slug = h.slug AND p2.stats_day = %s ORDER BY p2.part DESC LIMIT 4) t) AS top
        FROM hunts h JOIN agg ON agg.slug = h.slug
        WHERE round(agg.kills) > 0
        ORDER BY kills DESC
        """,
        w["id"], chosen, trend_days, chosen, chosen, chosen, chosen, chosen,
    )
    base_n = sum(1 for d in available if chosen - timedelta(days=trend_days) <= d < chosen)
    trends = (await flags()).get("page_hunt_trends", True)
    for r in rows:
        base = r.pop("base_kills") / base_n if base_n else None
        r["delta_pct"] = round((r["kills"] - base) / base * 100) if trends and base_n >= 3 and base and base >= 50 else None
        r["risk"] = round(r["deaths"] / r["kills"] * 1000, 1) if trends and r["kills"] >= 100 else None
        if not trends:
            r.pop("deaths")
    creatures = await query(
        """
        WITH base AS (SELECT race, sum(killed)::float AS killed FROM kill_stats_daily
                      WHERE world_id = %s AND stats_day >= %s::date - %s AND stats_day < %s GROUP BY race)
        SELECT k.race, k.killed, k.players_killed, coalesce(b.killed, 0) AS base_killed
        FROM kill_stats_daily k LEFT JOIN base b ON b.race = k.race
        WHERE k.world_id = %s AND k.stats_day = %s ORDER BY k.killed DESC LIMIT 15
        """,
        w["id"], chosen, trend_days, chosen, w["id"], chosen,
    )
    for c in creatures:
        base = c.pop("base_killed") / base_n if base_n else None
        c["delta_pct"] = round((c["killed"] - base) / base * 100) if trends and base_n >= 3 and base and base >= 50 else None
        c["risk"] = round(c["players_killed"] / c["killed"] * 1000, 1) if trends and c["killed"] >= 100 else None
    totals = (await query(
        "SELECT sum(killed)::int AS killed, sum(players_killed)::int AS deaths FROM kill_stats_daily "
        "WHERE world_id = %s AND stats_day = %s",
        w["id"], chosen,
    ))[0]
    cache(response, 900)
    return {"world": w["name"], "day": chosen, "days": available, "hunts": rows, "bounds": MAP_BOUNDS,
            "creatures": creatures, "totals": totals, "trend_days": trend_days, "base_days": base_n, "trends": trends}



# ---------------------------------------------------------------- wrapped (resumo do mês)
# Só totais mensais e diários: nenhum horário. Quem fez opt-out não tem Wrapped.

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
NOT_OPTED = "NOT EXISTS (SELECT 1 FROM privacy_optouts p WHERE lower(p.name) = lower({col}))"


def month_range(month: str | None) -> tuple[datetime, datetime, bool]:
    today = datetime.now(timezone.utc).date()
    if month:
        if not MONTH_RE.match(month):
            raise HTTPException(422, "mês inválido (use AAAA-MM)")
        y, m = map(int, month.split("-"))
    else:
        y, m = today.year, today.month
    start = datetime(y, m, 1).date()
    end = datetime(y + (m == 12), 1 if m == 12 else m + 1, 1).date()
    return start, end, start <= today < end


@app.get("/v1/wrapped/{name_world}/{name}")
async def wrapped_character(name_world: str, name: str, response: Response, month: str | None = None):
    await require("page_wrapped")
    w = await world_or_404(name_world)
    start, end, partial = month_range(month)
    found = await query(
        f"SELECT id, name, level, vocation, first_seen_day FROM characters "
        f"WHERE world_id = %s AND lower(name) = lower(%s) AND {NOT_OPTED.format(col='name')}",
        w["id"], name,
    )
    if not found:
        raise HTTPException(404, "personagem não encontrado neste mundo")
    c = found[0]
    totals = (await query(
        """
        SELECT coalesce(sum(minutes), 0)::int AS minutes, count(*)::int AS days,
               max(minutes)::int AS best_day_minutes
        FROM daily_online WHERE character_id = %s AND game_day >= %s AND game_day < %s
        """,
        c["id"], start, end,
    ))[0]
    weekday = await query(
        """
        SELECT extract(isodow FROM game_day)::int AS dow, sum(minutes)::int AS minutes
        FROM daily_online WHERE character_id = %s AND game_day >= %s AND game_day < %s
        GROUP BY 1 ORDER BY 2 DESC LIMIT 1
        """,
        c["id"], start, end,
    )
    rank = (await query(
        """
        WITH totals AS (
          SELECT d.character_id, sum(d.minutes) AS m FROM daily_online d
          JOIN characters x ON x.id = d.character_id
          WHERE x.world_id = %s AND d.game_day >= %s AND d.game_day < %s GROUP BY d.character_id
        )
        SELECT count(*)::int AS players,
               count(*) FILTER (WHERE m > (SELECT coalesce(max(m), 0) FROM totals WHERE character_id = %s))::int AS ahead
        FROM totals
        """,
        w["id"], start, end, c["id"],
    ))[0]
    levels = await query(
        "SELECT level_start, level_end FROM monthly_level WHERE character_id = %s AND month = %s", c["id"], start,
    )
    guild = await query(
        "SELECT g.name, m.rank FROM guild_members m JOIN guilds g ON g.id = m.guild_id "
        "WHERE lower(m.name) = lower(%s) AND g.disbanded_day IS NULL LIMIT 1",
        c["name"],
    )
    top_percent = None
    if totals["minutes"] and rank["players"]:
        top_percent = max(1, round(100 * (rank["ahead"] + 1) / rank["players"]))
    lv = levels[0] if levels else None
    cache(response, 900)
    return {
        "world": w["name"], "name": c["name"], "vocation": c["vocation"], "level": c["level"],
        "month": start.strftime("%Y-%m"), "partial": partial,
        "minutes": totals["minutes"], "days_active": totals["days"], "best_day_minutes": totals["best_day_minutes"],
        "favorite_weekday": weekday[0]["dow"] if weekday else None,
        "levels_gained": (lv["level_end"] - lv["level_start"]) if lv else 0,
        "level_start": lv["level_start"] if lv else None, "level_end": lv["level_end"] if lv else None,
        "top_percent": top_percent, "world_players": rank["players"],
        "guild": guild[0] if guild else None, "first_seen_day": c["first_seen_day"],
    }


@app.get("/v1/wrapped-world/{name}")
async def wrapped_world(name: str, response: Response, month: str | None = None):
    await require("page_wrapped")
    w = await world_or_404(name)
    start, end, partial = month_range(month)
    online = (await query(
        """
        SELECT round(avg(players_online))::int AS avg_online, max(players_online) AS peak,
               (array_agg(ts ORDER BY players_online DESC))[1] AS peak_at
        FROM world_online_5m WHERE world_id = %s AND ts >= %s AND ts < %s
        """,
        w["id"], start, end,
    ))[0]
    deaths = (await query(
        "SELECT coalesce(sum(players_killed), 0)::int AS deaths, coalesce(sum(killed), 0)::bigint AS kills "
        "FROM kill_stats_daily WHERE world_id = %s AND stats_day >= %s AND stats_day < %s",
        w["id"], start, end,
    ))[0]
    creatures = await query(
        """
        SELECT race, sum(killed)::bigint AS killed FROM kill_stats_daily
        WHERE world_id = %s AND stats_day >= %s AND stats_day < %s
        GROUP BY race ORDER BY killed DESC LIMIT 5
        """,
        w["id"], start, end,
    )
    killers = await query(
        """
        SELECT race, sum(players_killed)::int AS players_killed FROM kill_stats_daily
        WHERE world_id = %s AND stats_day >= %s AND stats_day < %s AND players_killed > 0
        GROUP BY race ORDER BY players_killed DESC LIMIT 5
        """,
        w["id"], start, end,
    )
    new_chars = (await query(
        f"""
        WITH s AS (SELECT min(first_seen_day) AS start_day FROM characters WHERE world_id = %s)
        SELECT count(*)::int AS n FROM characters c, s
        WHERE c.world_id = %s AND c.first_level <= %s AND c.first_seen_day > s.start_day
          AND c.first_seen_day >= %s AND c.first_seen_day < %s
        """,
        w["id"], w["id"], PARAM["new_level_max"], start, end,
    ))[0]["n"]
    transfers = (await query(
        "SELECT count(*) FILTER (WHERE to_world_id = %s)::int AS arrived, "
        "count(*) FILTER (WHERE from_world_id = %s)::int AS left "
        "FROM transfers WHERE detected_day >= %s AND detected_day < %s",
        w["id"], w["id"], start, end,
    ))[0]
    levels = (await query(
        "SELECT coalesce(sum(level_end - level_start), 0)::int AS levels FROM monthly_level ml "
        "JOIN characters c ON c.id = ml.character_id WHERE c.world_id = %s AND ml.month = %s",
        w["id"], start,
    ))[0]["levels"]
    cache(response, 900)
    return {"world": w["name"], "month": start.strftime("%Y-%m"), "partial": partial, **online, **deaths,
            "top_creatures": creatures, "top_killers": killers, "new_characters": new_chars,
            "transfers": transfers, "levels_gained": levels}


@app.get("/v1/wrapped-guild/{world_name}/{guild}")
async def wrapped_guild(world_name: str, guild: str, response: Response, month: str | None = None):
    await require("page_wrapped")
    w = await world_or_404(world_name)
    start, end, partial = month_range(month)
    found = await query("SELECT id, name, members_total FROM guilds WHERE world_id = %s AND lower(name) = lower(%s)",
                        w["id"], guild)
    if not found:
        raise HTTPException(404, "guild não encontrada")
    g = found[0]
    events = (await query(
        "SELECT count(*) FILTER (WHERE event = 'join')::int AS joins, count(*) FILTER (WHERE event = 'leave')::int AS leaves "
        "FROM guild_events WHERE guild_id = %s AND event_day >= %s AND event_day < %s",
        g["id"], start, end,
    ))[0]
    members = (await query(
        f"""
        WITH m AS (
          SELECT c.id FROM guild_members gm JOIN characters c ON lower(c.name) = lower(gm.name)
          WHERE gm.guild_id = %s AND {NOT_OPTED.format(col='gm.name')}
        )
        SELECT (SELECT coalesce(sum(minutes), 0)::bigint FROM daily_online d JOIN m ON m.id = d.character_id
                 WHERE d.game_day >= %s AND d.game_day < %s) AS minutes,
               (SELECT coalesce(sum(level_end - level_start), 0)::int FROM monthly_level ml JOIN m ON m.id = ml.character_id
                 WHERE ml.month = %s) AS levels_gained,
               (SELECT count(DISTINCT d.character_id)::int FROM daily_online d JOIN m ON m.id = d.character_id
                 WHERE d.game_day >= %s AND d.game_day < %s) AS active_members
        """,
        g["id"], start, end, start, start, end,
    ))[0]
    top_levels = await query(
        f"""
        SELECT gm.name, ml.level_end - ml.level_start AS gained, ml.level_end
        FROM guild_members gm JOIN characters c ON lower(c.name) = lower(gm.name)
        JOIN monthly_level ml ON ml.character_id = c.id AND ml.month = %s
        WHERE gm.guild_id = %s AND {NOT_OPTED.format(col='gm.name')} AND ml.level_end > ml.level_start
        ORDER BY gained DESC, gm.name LIMIT 5
        """,
        start, g["id"],
    )
    cache(response, 900)
    return {"world": w["name"], "guild": g["name"], "members_total": g["members_total"],
            "month": start.strftime("%Y-%m"), "partial": partial, **events, **members, "top_levels": top_levels}


# ---------------------------------------------------------------- feature flags
# /v1/flags é público (o site usa para esconder o que está desligado).
# /v1/admin/* não passa pelo Caddy: só o container do site, na rede interna, consegue chamar.


class FlagIn(BaseModel):
    key: str
    enabled: bool


@app.get("/v1/flags")
async def public_flags(response: Response):
    response.headers["Cache-Control"] = "public, max-age=10"
    return await flags()


@app.get("/v1/admin/flags")
async def admin_flags(response: Response):
    response.headers["Cache-Control"] = "no-store"
    rows = {r["key"]: r for r in await query("SELECT key, enabled, updated_at FROM feature_flags")}
    paused = (await app.state.redis.get("seismo:paused")) == "1"
    return {
        "collector_paused": paused,
        "flags": [{**f, "enabled": rows[f["key"]]["enabled"] if f["key"] in rows else True,
                   "updated_at": rows[f["key"]]["updated_at"] if f["key"] in rows else None} for f in FLAGS],
    }


@app.post("/v1/admin/flags")
async def admin_set_flag(body: FlagIn, response: Response):
    response.headers["Cache-Control"] = "no-store"
    if body.key == "collector_online":
        await app.state.redis.set("seismo:paused", "0" if body.enabled else "1")
        return {"key": body.key, "enabled": body.enabled}
    if body.key not in DEFAULTS:
        raise HTTPException(422, "flag desconhecida")
    await query(
        "INSERT INTO feature_flags (key, enabled, updated_at) VALUES (%s, %s, now()) "
        "ON CONFLICT (key) DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = now()",
        body.key, body.enabled,
    )
    _flags_cache["at"] = 0.0
    return {"key": body.key, "enabled": body.enabled}


class ParamIn(BaseModel):
    key: str
    value: str | int | float | bool | None = None   # None = voltar ao padrão


@app.get("/v1/params")
async def public_params(response: Response):
    """Só os parâmetros marcados como públicos (ex.: e-mail de contato)."""
    p = await params()
    response.headers["Cache-Control"] = "public, max-age=10"
    return {k: p[k] for k, meta in BY_KEY.items() if meta.get("public")}


@app.get("/v1/admin/params")
async def admin_params(response: Response):
    response.headers["Cache-Control"] = "no-store"
    rows = {r["key"]: r for r in await query("SELECT key, value, updated_at FROM app_settings")}
    effective_raw = await app.state.redis.get("seismo:params:effective")
    import json as _json
    effective = _json.loads(effective_raw) if effective_raw else {}
    out = []
    for meta in PARAMS:
        stored = rows.get(meta["key"])
        out.append({**meta, "value": stored["value"] if stored else meta["default"], "custom": bool(stored),
                    "updated_at": stored["updated_at"] if stored else None,
                    "collector_value": effective.get(meta["key"])})
    return {"params": out}


@app.post("/v1/admin/params")
async def admin_set_param(body: ParamIn, response: Response):
    response.headers["Cache-Control"] = "no-store"
    if body.key not in BY_KEY:
        raise HTTPException(422, "parâmetro desconhecido")
    if body.value is None or body.value == "":
        if BY_KEY[body.key]["type"] != "str" or body.value is None:
            await query("DELETE FROM app_settings WHERE key = %s", body.key)
            _params_cache["at"] = 0.0
            return {"key": body.key, "value": BY_KEY[body.key]["default"], "custom": False}
    try:
        value = validate(body.key, body.value)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc))
    from psycopg.types.json import Jsonb
    await query(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (%s, %s, now()) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()",
        body.key, Jsonb(value),
    )
    _params_cache["at"] = 0.0
    return {"key": body.key, "value": value, "custom": True}


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


# rotas de insights (módulo separado para este arquivo não crescer demais)
from . import insights  # noqa: E402

app.include_router(insights.router)
