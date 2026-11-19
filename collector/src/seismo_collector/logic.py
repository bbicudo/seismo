"""Regras puras do coletor (sem rede, sem banco). Testadas em selftest.py."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
SERVER_SAVE_HOUR = 10  # o dia de jogo vira às 10:00 de Berlim


def level_band(level: int) -> str:
    if level < 100:
        return "1-99"
    if level < 300:
        return "100-299"
    if level < 600:
        return "300-599"
    return "600+"


def game_day(ts: datetime) -> date:
    """Dia de jogo de um instante (UTC ou com fuso). Antes do server save ainda é o dia anterior."""
    local = ts.astimezone(BERLIN)
    return (local - timedelta(hours=SERVER_SAVE_HOUR)).date()


def next_server_save(ts: datetime) -> datetime:
    local = ts.astimezone(BERLIN)
    save = local.replace(hour=SERVER_SAVE_HOUR, minute=0, second=0, microsecond=0)
    if save <= local:
        save = (local + timedelta(days=1)).replace(hour=SERVER_SAVE_HOUR, minute=0, second=0, microsecond=0)
    return save.astimezone(timezone.utc)


def split_minutes(start: datetime, end: datetime) -> dict[date, int]:
    """Divide uma sessão online em minutos por dia de jogo (corta no server save)."""
    out: dict[date, int] = {}
    cur = start
    while cur < end:
        boundary = min(next_server_save(cur), end)
        minutes = round((boundary - cur).total_seconds() / 60)
        if minutes > 0:
            day = game_day(cur)
            out[day] = out.get(day, 0) + minutes
        cur = boundary
    return out


def encode_player(level: int, vocation: str) -> str:
    return f"{level}|{vocation}"


def decode_player(value: str) -> tuple[int, str]:
    level, _, vocation = value.partition("|")
    return int(level or 0), vocation


@dataclass
class Diff:
    logins: list[str] = field(default_factory=list)
    logouts: list[str] = field(default_factory=list)
    level_changes: list[tuple[str, int, int]] = field(default_factory=list)
    vocation_changes: list[tuple[str, str]] = field(default_factory=list)


def diff_snapshots(prev: dict[str, str], curr: dict[str, str]) -> Diff:
    """prev/curr: nome -> "level|vocação". Tudo em ordem alfabética para ser determinístico."""
    d = Diff()
    d.logins = sorted(curr.keys() - prev.keys())
    d.logouts = sorted(prev.keys() - curr.keys())
    for name in sorted(prev.keys() & curr.keys()):
        old_level, old_voc = decode_player(prev[name])
        new_level, new_voc = decode_player(curr[name])
        if new_level != old_level:
            d.level_changes.append((name, old_level, new_level))
        if new_voc != old_voc:
            d.vocation_changes.append((name, new_voc))
    return d


def activity_counts(curr: dict[str, str]) -> dict[tuple[str, str], int]:
    """Contagem anônima vocação × faixa de level de uma foto."""
    out: dict[tuple[str, str], int] = {}
    for value in curr.values():
        level, vocation = decode_player(value)
        key = (vocation or "None", level_band(level))
        out[key] = out.get(key, 0) + 1
    return out


def hour_bucket(ts: datetime) -> datetime:
    return ts.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def cycle_slot(ts: datetime, interval: int) -> datetime:
    """Arredonda para baixo no múltiplo do intervalo (ex.: 10:07 -> 10:05)."""
    epoch = int(ts.timestamp())
    return datetime.fromtimestamp(epoch - epoch % interval, tz=timezone.utc)
