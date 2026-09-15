import random

from game import data_loader
from game.systems.catalog import Catalog
from game.systems.status import StatusEffects, speed_for, try_inflict
from tests.helpers import FixedRng

CATALOG = Catalog.from_data(data_loader.load_all())
S = CATALOG.statuses


def test_status_expires_after_duration():
    effects = StatusEffects()
    effects.add(S["poison"])
    for _ in range(S["poison"].duration - 1):
        assert effects.tick() == []
    assert effects.tick() == ["poison"]
    assert "poison" not in effects


def test_same_status_keeps_longer_duration():
    effects = StatusEffects()
    effects.add(S["poison"], 3)
    effects.add(S["poison"], 8)
    assert effects.remaining("poison") == 8
    effects.add(S["poison"], 2)
    assert effects.remaining("poison") == 8


def test_max_hp_down_stacks_until_floor_change():
    effects = StatusEffects()
    effects.add(S["max_hp_down"])
    effects.add(S["max_hp_down"])
    for _ in range(100):
        effects.tick()
    assert effects.stacks("max_hp_down") == 2
    assert effects.clear_until_floor_change() == {"max_hp_down": 2}
    assert "max_hp_down" not in effects


def test_poison_resist_blocks_poison():
    effects = StatusEffects()
    effects.add(S["poison_resist"])
    assert not try_inflict(effects, S["poison"], random.Random(0))
    assert "poison" not in effects


def test_status_resist_halves_chance():
    effects = StatusEffects()
    effects.add(S["status_resist"])
    # 確率 100% が 50% になる: 出目 60 では防げる、出目 10 ではかかる
    assert not try_inflict(effects, S["confusion"], FixedRng(60))
    assert try_inflict(effects, S["confusion"], FixedRng(10))


def test_buffs_are_not_affected_by_status_resist():
    effects = StatusEffects()
    effects.add(S["status_resist"])
    assert try_inflict(effects, S["atk_up"], FixedRng(99))


def test_speed_for_slow_and_haste():
    effects = StatusEffects()
    assert speed_for(effects, S) == 100
    effects.add(S["slow"])
    assert speed_for(effects, S) == 50
    effects.add(S["haste"])
    assert speed_for(effects, S) == 100
    effects.remove("slow")
    assert speed_for(effects, S) == 200
