"""Insights agregados: índice de saúde dos mundos, fluxo de transfers, vocações, novatos (funil e retenção),
velocidade de up, vitalidade e troca de membros entre guilds, mercado de casas e impacto de eventos.

Tudo aqui é soma ou média de muitos personagens. Grupos menores que o tamanho mínimo (min_cell) não aparecem.
As contas mais pesadas ficam em memória por alguns minutos (memo) para não repetir no banco a cada visita.
"""

import time
from datetime import date, timedelta
from statistics import median

from fastapi import APIRouter, HTTPException, Response

from . import main as m

router = APIRouter()

_memo: dict = {}


async def memo(key, ttl: int, fn):
    hit = _memo.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    value = await fn()
    _memo[key] = (time.monotonic(), value)
    return value


def voc_case(col: str = "vocation") -> str:
    """CASE em SQL que junta a vocação promovida com a base (Elite Knight -> knight)."""
    parts = " ".join(f"WHEN {col} IN ({', '.join(repr(v) for v in names)}) THEN '{base}'"
                     for base, names in m.VOCATION_GROUPS.items() if base != "none")
    return f"(CASE {parts} ELSE 'none' END)"


BAND_CASE = "(CASE WHEN {c} < 100 THEN '1-99' WHEN {c} < 300 THEN '100-299' WHEN {c} < 600 THEN '300-599' ELSE '600+' END)"
BAND_ORDER = ["1-99", "100-299", "300-599", "600+"]
VOC_ORDER = ["knight", "paladin", "sorcerer", "druid", "monk", "none"]


def int_list(text: str, limit: int) -> list[int]:
    return sorted({int(x) for x in str(text).replace(" ", "").split(",") if x.isdigit()})[:limit]


def pct_rank(values: dict) -> dict:
    """Posição de cada valor entre os outros, de 0 a 1 (empates ficam no meio)."""
    vals = [v for v in values.values() if v is not None]
    n = len(vals)
    out = {}
    for k, v in values.items():
        if v is None:
            out[k] = None
        elif n == 1:
            out[k] = 0.5
        else:
            less = sum(1 for x in vals if x < v)
            equal = sum(1 for x in vals if x == v)
            out[k] = (less + (equal - 1) / 2) / (n - 1)
    return out


# ---------------------------------------------------------------- índice de saúde

async def health_raw(window: int, new_max: int) -> dict:
    """Valores brutos por mundo: tendência de online, retenção, personagens novos e saldo de transfers."""
    started = (await m.query("SELECT min(ts) AS t, (SELECT min(game_day) FROM daily_online) AS d FROM world_online_5m"))[0]
    rows = await m.query(
        """
        WITH online AS (
          SELECT world_id,
                 avg(players_online) FILTER (WHERE ts > now() - make_interval(days => %s)) AS cur,
                 avg(players_online) FILTER (WHERE ts <= now() - make_interval(days => %s)) AS prev
          FROM world_online_5m WHERE ts > now() - make_interval(days => %s) GROUP BY world_id
        ),
        prev_players AS (
          SELECT DISTINCT character_id FROM daily_online
          WHERE game_day > current_date - %s AND game_day <= current_date - %s
        ),
        ret AS (
          SELECT c.world_id, count(*) AS base, count(*) FILTER (WHERE c.last_seen_day > current_date - %s) AS kept
          FROM prev_players p JOIN characters c ON c.id = p.character_id GROUP BY c.world_id
        ),
        starts AS (SELECT world_id, min(first_seen_day) AS start_day FROM characters GROUP BY world_id),
        fresh AS (
          SELECT c.world_id, count(*) AS n FROM characters c JOIN starts s ON s.world_id = c.world_id
          WHERE c.first_level <= %s AND c.first_seen_day > s.start_day AND c.first_seen_day > current_date - %s
          GROUP BY c.world_id
        ),
        moves AS (
          SELECT w.id AS world_id,
                 (SELECT count(*) FROM transfers t WHERE t.to_world_id = w.id AND t.detected_day > current_date - %s)
               - (SELECT count(*) FROM transfers t WHERE t.from_world_id = w.id AND t.detected_day > current_date - %s) AS net
          FROM worlds w
        )
        SELECT w.name, w.location, w.pvp_type, w.players_online,
               o.cur::float AS online_cur, o.prev::float AS online_prev,
               r.base AS ret_base, r.kept AS ret_kept, coalesce(f.n, 0) AS new_chars, mv.net AS net_transfers
        FROM worlds w
        LEFT JOIN online o ON o.world_id = w.id
        LEFT JOIN ret r ON r.world_id = w.id
        LEFT JOIN fresh f ON f.world_id = w.id
        LEFT JOIN moves mv ON mv.world_id = w.id
        """,
        window, window, 2 * window, 2 * window, window, window, new_max, window, window, window,
    )
    return {"started_at": started["t"], "daily_since": started["d"], "rows": rows}


def score_worlds(raw: dict, window: int, weights: dict) -> dict:
    from datetime import datetime, timezone
    started = raw["started_at"]
    have_days = (datetime.now(timezone.utc) - started).total_seconds() / 86400 if started else 0
    ready = have_days >= 2 * window
    rows = raw["rows"]
    parts = {"trend": {}, "retention": {}, "new": {}, "transfers": {}}
    out = []
    for r in rows:
        cur, prev = r["online_cur"], r["online_prev"]
        trend = (cur - prev) / prev * 100 if cur and prev else None
        base = r["ret_base"] or 0
        retention = r["ret_kept"] / base * 100 if base >= 20 else None
        per_k = 1000 / cur if cur and cur >= 5 else None
        new_k = r["new_chars"] * per_k if per_k else None
        net_k = r["net_transfers"] * per_k if per_k and r["net_transfers"] is not None else None
        parts["trend"][r["name"]] = trend
        parts["retention"][r["name"]] = retention
        parts["new"][r["name"]] = new_k
        parts["transfers"][r["name"]] = net_k
        out.append({"name": r["name"], "location": r["location"], "pvp_type": r["pvp_type"],
                    "players_online": r["players_online"],
                    "trend_pct": round(trend, 1) if trend is not None else None,
                    "retention_pct": round(retention, 1) if retention is not None else None,
                    "new_per_1k": round(new_k, 1) if new_k is not None else None,
                    "net_transfers_per_1k": round(net_k, 1) if net_k is not None else None,
                    "net_transfers": r["net_transfers"], "new_characters": r["new_chars"]})
    ranks = {k: pct_rank(v) for k, v in parts.items()}
    for o in out:
        num = den = 0.0
        for k, wgt in weights.items():
            p = ranks[k][o["name"]]
            if p is not None and wgt > 0:
                num += p * wgt
                den += wgt
        o["score"] = round(num / den * 100) if ready and den > 0 else None
    scored = sorted((o for o in out if o["score"] is not None), key=lambda o: -o["score"])
    for i, o in enumerate(scored, 1):
        o["rank"] = i
    return {"window": window, "ready": ready, "days_collected": round(have_days, 1),
            "days_needed": 2 * window, "total": len(scored), "worlds": out}


async def health_all() -> dict:
    p = await m.params()
    window = p["health_window_days"]
    raw = await memo(("health", window, p["new_level_max"]), 900, lambda: health_raw(window, p["new_level_max"]))
    weights = {"trend": p["health_w_trend"], "retention": p["health_w_retention"],
               "new": p["health_w_new"], "transfers": p["health_w_transfers"]}
    return score_worlds(raw, window, weights)


@router.get("/v1/insights/health")
async def insights_health(response: Response):
    await m.require("page_health_index")
    d = await health_all()
    m.cache(response, 300)
    return d


@router.get("/v1/worlds/{name}/summary")
async def world_summary(name: str, response: Response):
    """Cabeçalho leve de todas as abas do mundo."""
    w = await m.world_or_404(name)
    record = await m.query(
        "SELECT ts, players_online FROM world_online_5m WHERE world_id = %s ORDER BY players_online DESC, ts LIMIT 1",
        w["id"],
    )
    since = await m.query("SELECT min(ts) AS since FROM world_online_5m WHERE world_id = %s", w["id"])
    health = None
    if (await m.flags()).get("page_health_index", True):
        h = await health_all()
        mine = next((x for x in h["worlds"] if x["name"] == w["name"]), None)
        health = {**{k: h[k] for k in ("window", "ready", "days_collected", "days_needed", "total")}, **(mine or {})}
    wid = w.pop("id")
    m.cache(response, 60)
    return {**w, "record": record[0] if record else None, "collecting_since": since[0]["since"], "health": health}


# ---------------------------------------------------------------- fluxo de transfers

@router.get("/v1/worlds/{name}/flows")
async def world_flows(name: str, response: Response):
    await m.require("page_transfer_flows")
    w = await m.world_or_404(name)
    days, top = m.PARAM["flows_days"], m.PARAM["flows_top"]
    arrived = await m.query(
        "SELECT o.name AS world, count(*)::int AS n FROM transfers t JOIN worlds o ON o.id = t.from_world_id "
        "WHERE t.to_world_id = %s AND t.detected_day > current_date - %s GROUP BY o.name ORDER BY n DESC, o.name",
        w["id"], days,
    )
    left = await m.query(
        "SELECT o.name AS world, count(*)::int AS n FROM transfers t JOIN worlds o ON o.id = t.to_world_id "
        "WHERE t.from_world_id = %s AND t.detected_day > current_date - %s GROUP BY o.name ORDER BY n DESC, o.name",
        w["id"], days,
    )
    m.cache(response, 900)
    return {"world": w["name"], "days": days,
            "arrived_total": sum(r["n"] for r in arrived), "left_total": sum(r["n"] for r in left),
            "arrived": arrived[:top], "left": left[:top]}


# ---------------------------------------------------------------- vocações

@router.get("/v1/worlds/{name}/vocations")
async def world_vocations(name: str, response: Response):
    await m.require("page_vocations")
    w = await m.world_or_404(name)
    window, min_cell = m.PARAM["health_window_days"], m.PARAM["min_cell"]

    async def load():
        hrs = (await m.query(
            "SELECT count(*) FILTER (WHERE hour > now() - make_interval(days => %s))::int AS cur, "
            "count(*) FILTER (WHERE hour <= now() - make_interval(days => %s))::int AS prev "
            "FROM world_hour_snapshots WHERE world_id = %s AND hour > now() - make_interval(days => %s)",
            window, window, w["id"], 2 * window,
        ))[0]
        rows = await m.query(
            f"""
            SELECT {voc_case('b.vocation')} AS voc, b.level_band AS band,
                   coalesce(sum(b.samples::float / s.snapshots) FILTER (WHERE b.hour > now() - make_interval(days => %s)), 0) AS cur,
                   coalesce(sum(b.samples::float / s.snapshots) FILTER (WHERE b.hour <= now() - make_interval(days => %s)), 0) AS prev
            FROM activity_buckets b JOIN world_hour_snapshots s ON s.world_id = b.world_id AND s.hour = b.hour
            WHERE b.world_id = %s AND b.hour > now() - make_interval(days => %s)
            GROUP BY 1, 2
            """,
            window, window, w["id"], 2 * window,
        )
        return hrs, rows

    hrs, rows = await memo(("voc", w["id"], window), 900, load)
    cur_h, prev_h = hrs["cur"], hrs["prev"]
    table: dict[str, dict] = {}
    for r in rows:
        t = table.setdefault(r["voc"], {"vocation": r["voc"], "bands": {}, "cur": 0.0, "prev": 0.0})
        avg = r["cur"] / cur_h if cur_h else 0
        t["bands"][r["band"]] = avg
        t["cur"] += avg
        t["prev"] += r["prev"] / prev_h if prev_h else 0
    total_cur = sum(t["cur"] for t in table.values())
    total_prev = sum(t["prev"] for t in table.values())
    out = []
    for v in VOC_ORDER:
        t = table.get(v)
        if not t:
            continue
        share = t["cur"] / total_cur * 100 if total_cur else None
        share_prev = t["prev"] / total_prev * 100 if total_prev and prev_h >= 24 else None
        out.append({
            "vocation": v,
            "bands": {b: (round(t["bands"][b], 1) if t["bands"].get(b, 0) >= min_cell else None) for b in BAND_ORDER},
            "avg_online": round(t["cur"], 1) if t["cur"] >= min_cell else None,
            "share": round(share, 1) if share is not None and t["cur"] >= min_cell else None,
            "delta_pp": round(share - share_prev, 1) if share is not None and share_prev is not None and t["cur"] >= min_cell else None,
        })
    m.cache(response, 900)
    return {"world": w["name"], "window": window, "hours": cur_h, "compare": prev_h >= 24, "min_cell": min_cell,
            "bands": BAND_ORDER, "vocations": out}


# ---------------------------------------------------------------- novatos: funil e retenção

@router.get("/v1/worlds/{name}/newcomers")
async def world_newcomers(name: str, response: Response):
    f = await m.flags()
    if not (f.get("page_funnel", True) or f.get("page_retention", True)):
        raise HTTPException(404, "recurso desligado")
    w = await m.world_or_404(name)
    p = m.PARAM
    levels = int_list(p["funnel_levels"], 6)
    marks = int_list(p["retention_marks"], 4)
    weeks, new_max = p["funnel_weeks"], p["new_level_max"]
    lvl_sql = ", ".join("count(*) FILTER (WHERE c.level >= %s)::int" for _ in levels) or "0"
    mark_sql = ", ".join("count(*) FILTER (WHERE c.last_seen_day >= c.first_seen_day + %s)::int" for _ in marks) or "0"

    async def load():
        base = """
            WITH s AS (SELECT min(first_seen_day) AS start_day FROM characters WHERE world_id = %s)
            SELECT {cols} FROM characters c, s
            WHERE c.world_id = %s AND c.first_level <= %s AND c.first_seen_day > s.start_day
              AND c.first_seen_day > current_date - %s {group}
        """
        daily = await m.query(
            base.format(cols="c.first_seen_day AS day, count(*)::int AS n", group="GROUP BY 1 ORDER BY 1"),
            w["id"], w["id"], new_max, 30,
        )
        cohorts = await m.query(
            base.format(cols=f"date_trunc('week', c.first_seen_day)::date AS week, min(c.first_seen_day) AS first_day, "
                             f"count(*)::int AS created, ARRAY[{lvl_sql}] AS reached, ARRAY[{mark_sql}] AS kept",
                        group="GROUP BY 1 ORDER BY 1 DESC"),
            w["id"], *levels, *marks, w["id"], new_max, weeks * 7,
        )
        return daily, cohorts

    daily, cohorts = await memo(("newc", w["id"], tuple(levels), tuple(marks), weeks, new_max), 900, load)
    today = date.today()
    min_cell = p["min_cell"]
    created = sum(c["created"] for c in cohorts)
    funnel = [{"level": lv, "n": sum(c["reached"][i] for c in cohorts)} for i, lv in enumerate(levels)]
    rows = []
    for c in cohorts:
        week_end = c["week"] + timedelta(days=6)
        ret = []
        for i, mk in enumerate(marks):
            old_enough = week_end + timedelta(days=mk) <= today
            ret.append(round(c["kept"][i] / c["created"] * 100) if old_enough and c["created"] >= min_cell else None)
        rows.append({"week": c["week"], "created": c["created"], "retention": ret})
    m.cache(response, 900)
    return {"world": w["name"], "new_level_max": new_max, "levels": levels, "marks": marks, "weeks": weeks,
            "min_cell": min_cell, "daily": daily, "created": created, "funnel": funnel, "cohorts": rows}


# ---------------------------------------------------------------- velocidade de up

@router.get("/v1/worlds/{name}/leveling")
async def world_leveling(name: str, response: Response):
    await m.require("page_leveling")
    w = await m.world_or_404(name)
    min_hours, min_cell = m.PARAM["leveling_min_hours"], m.PARAM["min_cell"]

    async def load():
        return await m.query(
            f"""
            WITH since AS (SELECT date_trunc('month', current_date - 30)::date AS d),
            lv AS (
              SELECT ml.character_id, sum(ml.level_end - ml.level_start) AS gained, min(ml.level_start) AS lvl
              FROM monthly_level ml JOIN characters c ON c.id = ml.character_id, since
              WHERE c.world_id = %s AND ml.month >= since.d GROUP BY ml.character_id
            ),
            mins AS (
              SELECT d.character_id, sum(d.minutes) AS minutes
              FROM daily_online d JOIN characters c ON c.id = d.character_id, since
              WHERE c.world_id = %s AND d.game_day >= since.d GROUP BY d.character_id
            )
            SELECT {voc_case('c.vocation')} AS voc, {BAND_CASE.format(c='lv.lvl')} AS band,
                   count(*)::int AS players, sum(lv.gained)::float AS levels, sum(mins.minutes)::float / 60 AS hours
            FROM lv JOIN mins USING (character_id) JOIN characters c ON c.id = lv.character_id
            WHERE mins.minutes >= %s
            GROUP BY 1, 2
            """,
            w["id"], w["id"], min_hours * 60,
        )

    rows = await memo(("lvl", w["id"], min_hours), 1800, load)
    grid: dict[str, dict] = {}
    for r in rows:
        if r["voc"] == "none" and r["band"] != "1-99":
            continue
        ok = r["players"] >= min_cell and r["hours"] > 0
        grid.setdefault(r["voc"], {})[r["band"]] = {
            "players": r["players"] if ok else None,
            "levels_per_hour": round(r["levels"] / r["hours"], 3) if ok else None,
        }
    out = [{"vocation": v, "bands": {b: grid[v].get(b) for b in BAND_ORDER}} for v in VOC_ORDER if v in grid]
    m.cache(response, 1800)
    since = (date.today() - timedelta(days=30)).replace(day=1)
    return {"world": w["name"], "since": since, "min_hours": min_hours,
            "min_cell": min_cell, "bands": BAND_ORDER, "vocations": out}


# ---------------------------------------------------------------- guilds: vitalidade e trocas

GUILD_SORTS = {
    "members": "g.members_total DESC NULLS LAST",
    "active": "(mem.active::float / nullif(mem.n, 0)) DESC NULLS LAST",
    "net": "(coalesce(ev.joins, 0) - coalesce(ev.leaves, 0)) DESC",
    "level": "mem.avg_level DESC NULLS LAST",
}


@router.get("/v1/worlds/{name}/guilds")
async def world_guilds(name: str, response: Response, sort: str = "members", limit: int = 50):
    await m.require("page_guilds")
    if sort not in GUILD_SORTS:
        raise HTTPException(422, "sort deve ser members, active, net ou level")
    limit = max(10, min(limit, 200))
    w = await m.world_or_404(name)
    p = m.PARAM
    active_days, window, gap, min_cell = p["guild_active_days"], p["guild_window_days"], p["guild_exchange_gap_days"], p["min_cell"]
    rows = await m.query(
        f"""
        WITH mem AS (
          SELECT m.guild_id, count(*) AS n, avg(m.level) AS avg_level,
                 count(*) FILTER (WHERE c.last_seen_day > current_date - %s) AS active
          FROM guild_members m
          JOIN guilds g ON g.id = m.guild_id AND g.world_id = %s AND g.disbanded_day IS NULL
          LEFT JOIN characters c ON c.name = m.name
          GROUP BY m.guild_id
        ),
        ev AS (
          SELECT e.guild_id, count(*) FILTER (WHERE e.event = 'join') AS joins, count(*) FILTER (WHERE e.event = 'leave') AS leaves
          FROM guild_events e JOIN guilds g ON g.id = e.guild_id AND g.world_id = %s
          WHERE e.event_day > current_date - %s GROUP BY e.guild_id
        )
        SELECT g.name, g.members_total, g.in_war, g.founded, mem.n::int AS members_read,
               round(mem.avg_level)::int AS avg_level, mem.active::int AS active,
               coalesce(ev.joins, 0)::int AS joins, coalesce(ev.leaves, 0)::int AS leaves
        FROM guilds g LEFT JOIN mem ON mem.guild_id = g.id LEFT JOIN ev ON ev.guild_id = g.id
        WHERE g.world_id = %s AND g.disbanded_day IS NULL
        ORDER BY {GUILD_SORTS[sort]}, g.name LIMIT %s
        """,
        active_days, w["id"], w["id"], window, w["id"], limit,
    )
    for r in rows:
        r["active_pct"] = round(r["active"] / r["members_read"] * 100) if r["members_read"] else None
    totals = (await m.query(
        "SELECT count(*)::int AS guilds, "
        "(SELECT count(*) FROM guild_events e JOIN guilds g2 ON g2.id = e.guild_id WHERE g2.world_id = %s AND e.event = 'join' AND e.event_day > current_date - %s)::int AS joins, "
        "(SELECT count(*) FROM guild_events e JOIN guilds g2 ON g2.id = e.guild_id WHERE g2.world_id = %s AND e.event = 'leave' AND e.event_day > current_date - %s)::int AS leaves "
        "FROM guilds WHERE world_id = %s AND disbanded_day IS NULL",
        w["id"], window, w["id"], window, w["id"],
    ))[0]
    since = (await m.query("SELECT min(first_seen_day) AS d FROM characters WHERE world_id = %s", w["id"]))[0]["d"]
    exchanges = []
    if (await m.flags()).get("page_guild_exchange", True):
        exchanges = await m.query(
            """
            SELECT ga.name AS from_guild, gb.name AS to_guild, count(DISTINCT l.name)::int AS n
            FROM guild_events l
            JOIN guild_events j ON j.name = l.name AND j.event = 'join' AND j.guild_id <> l.guild_id
                 AND abs(j.event_day - l.event_day) <= %s
            JOIN guilds ga ON ga.id = l.guild_id
            JOIN guilds gb ON gb.id = j.guild_id
            WHERE l.event = 'leave' AND ga.world_id = %s AND gb.world_id = %s AND l.event_day > current_date - %s
            GROUP BY ga.name, gb.name HAVING count(DISTINCT l.name) >= %s
            ORDER BY n DESC, ga.name LIMIT 10
            """,
            gap, w["id"], w["id"], window, min_cell,
        )
    m.cache(response, 900)
    return {"world": w["name"], "sort": sort, "window": window, "active_days": active_days, "gap_days": gap,
            "min_cell": min_cell, "activity_since": since, **totals, "rows": rows, "exchanges": exchanges}


# ---------------------------------------------------------------- mercado de casas

@router.get("/v1/worlds/{name}/houses")
async def world_houses(name: str, response: Response):
    await m.require("page_houses")
    w = await m.world_or_404(name)
    window = m.PARAM["house_market_days"]

    async def load():
        return await m.query(
            """
            WITH lastday AS (SELECT max(snap_day) AS d FROM house_snapshots WHERE world_id = %s),
            cur AS (
              SELECT DISTINCT ON (s.house_id) s.house_id, s.rented, s.auctioned, s.current_bid
              FROM house_snapshots s, lastday WHERE s.world_id = %s AND s.snap_day >= lastday.d - 2
              ORDER BY s.house_id, s.snap_day DESC
            ),
            isl AS (
              SELECT house_id, snap_day, auctioned,
                     snap_day - (row_number() OVER (PARTITION BY house_id, auctioned ORDER BY snap_day))::int AS grp
              FROM house_snapshots WHERE world_id = %s AND snap_day > current_date - %s
            ),
            runs AS (SELECT house_id, max(snap_day) AS stop, count(*) AS days FROM isl WHERE auctioned GROUP BY house_id, grp),
            closed AS (
              SELECT r.house_id, r.days FROM runs r
              JOIN house_snapshots s ON s.world_id = %s AND s.house_id = r.house_id AND s.snap_day = r.stop + 1
                   AND s.rented AND NOT s.auctioned
            ),
            closed_h AS (SELECT house_id, count(*) AS n, avg(days) AS days FROM closed GROUP BY house_id),
            owners AS (
              SELECT house_id, count(*) FILTER (WHERE ended_day > current_date - %s) AS ended
              FROM house_owners WHERE world_id = %s GROUP BY house_id
            )
            SELECT h.town, count(*)::int AS total,
                   count(*) FILTER (WHERE cur.rented)::int AS rented,
                   count(*) FILTER (WHERE cur.auctioned)::int AS auctioned,
                   count(*) FILTER (WHERE cur.auctioned AND cur.current_bid > 0)::int AS with_bid,
                   round(avg(cur.current_bid) FILTER (WHERE cur.auctioned AND cur.current_bid > 0))::bigint AS avg_bid,
                   coalesce(sum(cl.n), 0)::int AS closed,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY cl.days)::float AS median_days,
                   coalesce(sum(o.ended), 0)::int AS owner_changes,
                   count(*) FILTER (WHERE h.details_fetched_at IS NOT NULL)::int AS owners_read
            FROM houses h
            LEFT JOIN cur ON cur.house_id = h.house_id
            LEFT JOIN closed_h cl ON cl.house_id = h.house_id
            LEFT JOIN owners o ON o.house_id = h.house_id
            WHERE h.world_id = %s
            GROUP BY h.town ORDER BY h.town
            """,
            w["id"], w["id"], w["id"], window, w["id"], window, w["id"], w["id"],
        )

    rows = await memo(("houses", w["id"], window), 900, load)
    for r in rows:
        r["occupancy_pct"] = round(r["rented"] / r["total"] * 100) if r["total"] else None
    tot = {k: sum(r[k] for r in rows) for k in ("total", "rented", "auctioned", "with_bid", "closed", "owner_changes", "owners_read")}
    tot["occupancy_pct"] = round(tot["rented"] / tot["total"] * 100) if tot["total"] else None
    days = [r["median_days"] for r in rows if r["median_days"] is not None]
    hist = (await m.query("SELECT count(DISTINCT snap_day)::int AS n FROM house_snapshots WHERE world_id = %s", w["id"]))[0]["n"]
    m.cache(response, 900)
    return {"world": w["name"], "window": window, "history_days": hist, "totals": tot,
            "median_days": median(days) if days else None, "towns": rows}


# ---------------------------------------------------------------- impacto de eventos e criatura do dia

async def game_today() -> date:
    rows = await m.query("SELECT ((now() AT TIME ZONE 'Europe/Berlin') - interval '10 hours')::date AS d")
    return rows[0]["d"]


async def impact_load(baseline_weeks: int, boosted_days: int) -> dict:
    span = 7 * baseline_weeks + 60
    online = await m.query(
        """
        SELECT ((ts AT TIME ZONE 'Europe/Berlin') - interval '10 hours')::date AS day, avg(total)::float AS online
        FROM (SELECT ts, sum(players_online) AS total FROM world_online_5m
              WHERE ts > now() - make_interval(days => %s) GROUP BY ts) x
        GROUP BY 1
        """,
        span,
    )
    kills = await m.query(
        "SELECT stats_day AS day, sum(killed)::float AS killed, sum(players_killed)::float AS deaths "
        "FROM kill_stats_daily WHERE stats_day > current_date - %s GROUP BY 1",
        span,
    )
    events = await m.query(
        "SELECT day, name, kind FROM game_events WHERE kind IN ('double_xp', 'double_skill', 'rapid_respawn') "
        "AND day > current_date - %s ORDER BY day",
        span,
    )
    boosted = await m.query(
        "SELECT day, creature FROM daily_boosted WHERE creature IS NOT NULL AND day > current_date - %s ORDER BY day DESC",
        boosted_days + 1,
    )
    names = sorted({x for b in boosted for x in (b["creature"].lower(), b["creature"].lower() + "s", b["creature"].lower() + "es")})
    race_kills = await m.query(
        "SELECT stats_day AS day, lower(race) AS race, sum(killed)::float AS killed FROM kill_stats_daily "
        "WHERE stats_day > current_date - %s AND lower(race) = ANY(%s) GROUP BY 1, 2",
        boosted_days + 30, names,
    ) if names else []
    all_boosted = await m.query("SELECT day, lower(creature) AS creature FROM daily_boosted WHERE day > current_date - %s",
                                boosted_days + 30)
    kill_days = {r["day"] for r in kills}
    return {"online": online, "kills": kills, "events": events, "boosted": boosted, "race_kills": race_kills,
            "all_boosted": all_boosted, "kill_days": kill_days}


def pct(a, b):
    return round((a - b) / b * 100, 1) if a is not None and b else None


@router.get("/v1/events/impact")
async def events_impact(response: Response):
    await m.require("page_events")
    await m.require("page_event_impact")
    p = await m.params()
    weeks, bdays = p["impact_baseline_weeks"], p["boosted_days"]
    d = await memo(("impact", weeks, bdays), 1800, lambda: impact_load(weeks, bdays))
    today = await game_today()
    online = {r["day"]: r["online"] for r in d["online"]}
    kills = {r["day"]: r for r in d["kills"]}
    event_days = {e["day"] for e in d["events"]}

    # períodos: dias seguidos com o mesmo evento
    periods: list[dict] = []
    for e in d["events"]:
        last = next((q for q in reversed(periods) if q["name"] == e["name"]), None)
        if last and (e["day"] - last["to"]).days == 1:
            last["to"] = e["day"]
            last["days"].append(e["day"])
        else:
            periods.append({"name": e["name"], "kind": e["kind"], "from": e["day"], "to": e["day"], "days": [e["day"]]})

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None

    out = []
    for q in periods:
        days = [x for x in q["days"] if x < today]
        if not days:
            out.append({"name": q["name"], "kind": q["kind"], "from": q["from"], "to": q["to"], "status": "upcoming"})
            continue
        base = [x - timedelta(days=7 * k) for x in days for k in range(1, weeks + 1)]
        base = [x for x in base if x not in event_days]
        ev_on, b_on = mean(online.get(x) for x in days), mean(online.get(x) for x in base)
        ev_k = mean(kills[x]["killed"] for x in days if x in kills)
        b_k = mean(kills[x]["killed"] for x in base if x in kills)
        ev_d = mean(kills[x]["deaths"] for x in days if x in kills)
        b_d = mean(kills[x]["deaths"] for x in base if x in kills)
        item = {"name": q["name"], "kind": q["kind"], "from": q["from"], "to": q["to"], "days": len(days),
                "online_pct": pct(ev_on, b_on), "kills_pct": pct(ev_k, b_k), "deaths_pct": pct(ev_d, b_d),
                "online": round(ev_on) if ev_on else None}
        item["status"] = "ok" if any(item[k] is not None for k in ("online_pct", "kills_pct", "deaths_pct")) else "no_baseline"
        out.append(item)
    out.reverse()

    # criatura do dia: mortes no dia contra a média dos 28 dias anteriores (sem dias em que ela foi a destacada)
    by_race_day: dict = {}
    for r in d["race_kills"]:
        by_race_day[(r["race"], r["day"])] = by_race_day.get((r["race"], r["day"]), 0) + r["killed"]
    boosted_on = {}
    for b in d["all_boosted"]:
        boosted_on.setdefault(b["creature"], set()).add(b["day"])
    rows = []
    for b in d["boosted"]:
        day, c = b["day"], b["creature"].lower()
        if day >= today or day not in d["kill_days"]:
            continue
        forms = (c, c + "s", c + "es")
        killed = sum(by_race_day.get((f, day), 0) for f in forms)
        base_days = [day - timedelta(days=i) for i in range(1, 29)]
        base_days = [x for x in base_days if x in d["kill_days"] and x not in boosted_on.get(c, set()) and x not in event_days]
        normal = (sum(sum(by_race_day.get((f, x), 0) for f in forms) for x in base_days) / len(base_days)) if len(base_days) >= 3 else None
        rows.append({"day": day, "creature": b["creature"], "kills": round(killed),
                     "normal": round(normal) if normal is not None else None,
                     "multiplier": round(killed / normal, 1) if normal else None, "base_days": len(base_days)})
    mults = [r["multiplier"] for r in rows if r["multiplier"] is not None]
    m.cache(response, 1800)
    return {"baseline_weeks": weeks, "events": out[:12], "boosted": rows,
            "boosted_median": round(median(mults), 1) if mults else None}
