"""Testes das regras puras. Rode: python -m seismo_collector.selftest"""

from datetime import date, datetime, timezone

from .events import event_kinds, parse_window
from .raids import load_seed, race_keys, spawn_kind
from .logic import (
    activity_counts, cycle_slot, decode_player, diff_snapshots, encode_player, game_day, level_band, split_minutes,
)


def utc(*a: int) -> datetime:
    return datetime(*a, tzinfo=timezone.utc)


def main() -> None:
    assert [level_band(x) for x in (1, 99, 100, 299, 300, 599, 600)] == \
        ["1-99", "1-99", "100-299", "100-299", "300-599", "300-599", "600+"]

    # inverno: Berlim = UTC+1, server save às 09:00 UTC
    assert game_day(utc(2026, 11, 18, 8, 59)) == date(2026, 11, 17)
    assert game_day(utc(2026, 11, 18, 9, 0)) == date(2026, 11, 18)
    # verão: Berlim = UTC+2, server save às 08:00 UTC
    assert game_day(utc(2026, 7, 1, 7, 59)) == date(2026, 6, 30)
    assert game_day(utc(2026, 7, 1, 8, 0)) == date(2026, 7, 1)

    # sessão que atravessa o server save é dividida entre os dois dias
    s = split_minutes(utc(2026, 11, 18, 8, 30), utc(2026, 11, 18, 9, 45))
    assert s == {date(2026, 11, 17): 30, date(2026, 11, 18): 45}, s
    assert split_minutes(utc(2026, 11, 18, 10, 0), utc(2026, 11, 18, 10, 5)) == {date(2026, 11, 18): 5}

    assert decode_player(encode_player(512, "Royal Paladin")) == (512, "Royal Paladin")
    prev = {"A": "290|Elder Druid", "B": "38|Elite Knight", "C": "512|Royal Paladin"}
    curr = {"A": "291|Elder Druid", "C": "512|Royal Paladin", "D": "120|Exalted Monk"}
    d = diff_snapshots(prev, curr)
    assert d.logins == ["D"] and d.logouts == ["B"], d
    assert d.level_changes == [("A", 290, 291)] and d.vocation_changes == [], d

    assert activity_counts(curr) == {
        ("Elder Druid", "100-299"): 1, ("Royal Paladin", "300-599"): 1, ("Exalted Monk", "100-299"): 1,
    }
    assert cycle_slot(utc(2026, 11, 18, 10, 7, 31), 300) == utc(2026, 11, 18, 10, 5)

    # nomes de criaturas como aparecem nas kill statistics
    assert "draptors" in race_keys("Draptor")
    assert "ghazbaran" in race_keys("Ghazbaran")
    assert "wolves" in race_keys("Wolf") and "dwarves" in race_keys("Dwarf")
    assert "midnight panthers" in race_keys("Midnight Panther")
    assert "fairies" in race_keys("Fairy")
    seed = load_seed()
    assert len(seed) > 50 and all(r["creatures"] for r in seed)
    assert spawn_kind("Raid, Unique, Unblockable") == "raid"
    assert spawn_kind("Regular, Raid") == "regular" and spawn_kind("") == "unknown"

    # janela de evento a partir do texto da notícia do tibia.com
    txt = "Between the server saves of November 20 and November 23 all monsters will yield twice the usual amount of experience"
    assert parse_window(txt, date(2026, 11, 13)) == [date(2026, 11, 20), date(2026, 11, 21), date(2026, 11, 22)]
    assert parse_window("server saves of December 30 and January 2", date(2026, 12, 20))[-1] == date(2027, 1, 1)
    assert event_kinds("Double XP and Double Skill Event", txt) == ["double_xp", "double_skill"]
    print("selftest ok")


if __name__ == "__main__":
    main()
