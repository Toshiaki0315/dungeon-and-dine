from dataclasses import replace

import pytest

from game import data_loader
from game.entities.player import Player, PlayerParams
from game.systems.catalog import Catalog
from game.systems.progression import (
    ProgressionParams,
    SurvivalParams,
    apply_turn_end,
    exp_to_next_level,
    gain_exp,
    recover_mp_on_descend,
)

DATA = data_loader.load_all()
BALANCE = DATA["balance"]
SKILLS = Catalog.from_data(DATA).skills
SURVIVAL = SurvivalParams.from_dict(BALANCE["survival"])
PROGRESSION = ProgressionParams.from_dict(BALANCE["progression"])
PLAYER = PlayerParams.from_dict(BALANCE["player"])


def new_player(**changes):
    return replace(Player.from_params(PLAYER), **changes)


@pytest.mark.parametrize(("level", "expected"), [(1, 10), (4, 80), (9, 270)])
def test_exp_to_next_level(level, expected):
    assert exp_to_next_level(level, PROGRESSION) == expected


def test_gain_exp_levels_up_and_raises_stats():
    player = new_player()
    messages = gain_exp(player, exp_to_next_level(1, PROGRESSION), PROGRESSION, SKILLS)
    assert player.level == 2
    assert player.exp == 0
    assert player.max_hp == PLAYER.hp + PROGRESSION.hp_per_level
    assert player.max_mp == PLAYER.mp + PROGRESSION.mp_per_level
    assert player.atk == PLAYER.atk + PROGRESSION.atk_per_level
    assert player.defense == PLAYER.defense  # 偶数レベルでは防御は上がらない
    assert any("レベル2" in m for m in messages)


def test_gain_exp_can_level_up_multiple_times_and_learn_skills():
    player = new_player()
    total = exp_to_next_level(1, PROGRESSION) + exp_to_next_level(2, PROGRESSION) + 1
    messages = gain_exp(player, total, PROGRESSION, SKILLS)
    assert player.level == 3
    assert player.exp == 1
    assert player.defense == PLAYER.defense + PROGRESSION.def_per_odd_level
    assert "power_strike" in player.skills
    assert any("強撃" in m for m in messages)


def test_level_is_capped():
    player = new_player(level=PROGRESSION.max_level)
    gain_exp(player, 10**9, PROGRESSION, SKILLS)
    assert player.level == PROGRESSION.max_level


def test_poison_stops_hp_regeneration():
    player = new_player(hp=10)
    run_turns(player, 1, SURVIVAL.hp_regen_interval, can_regen_hp=False)
    assert player.hp == 10


def run_turns(player, start, count, **kwargs):
    messages = []
    for turn in range(start, start + count):
        messages += apply_turn_end(player, turn, SURVIVAL, **kwargs)
    return messages


def test_satiety_decreases_by_one_per_interval():
    player = new_player()
    run_turns(player, 1, SURVIVAL.satiety_decay_interval * 3)
    assert player.satiety == PLAYER.satiety - 3


def test_hunger_rate_percent_changes_decay_speed():
    player = new_player()
    interval = SURVIVAL.satiety_decay_interval
    run_turns(player, 1, interval * 10, hunger_rate_percent=80)
    assert player.satiety == PLAYER.satiety - 8
    player = new_player()
    run_turns(player, 1, interval * 10, hunger_rate_percent=200)
    assert player.satiety == PLAYER.satiety - 20


def test_hunger_warning_is_logged_once_when_crossing_threshold():
    threshold = SURVIVAL.hunger_warning_threshold
    player = new_player(satiety=threshold + 1)
    messages = run_turns(player, 1, SURVIVAL.satiety_decay_interval * 2)
    assert player.satiety == threshold - 1
    assert sum("おなかが減ってきた" in m for m in messages) == 1


def test_starving_damages_hp_and_stops_regeneration():
    player = new_player(satiety=1, hp=10, mp=0, satiety_progress=0)
    messages = run_turns(player, 1, SURVIVAL.satiety_decay_interval)
    assert player.satiety == 0
    assert any("飢えている" in m for m in messages)

    hp = player.hp
    mp = player.mp
    turns = SURVIVAL.hp_regen_interval * SURVIVAL.mp_regen_interval
    run_turns(player, 1, turns)
    assert player.hp == max(0, hp - SURVIVAL.starvation_damage * turns)
    assert player.mp == mp


def test_hp_and_mp_regenerate_on_interval():
    player = new_player(hp=10, mp=0)
    run_turns(player, 1, SURVIVAL.mp_regen_interval)
    regen_count = SURVIVAL.mp_regen_interval // SURVIVAL.hp_regen_interval
    assert player.hp == 10 + SURVIVAL.hp_regen_amount * regen_count
    assert player.mp == SURVIVAL.mp_regen_amount


def test_regeneration_does_not_exceed_max():
    player = new_player()
    run_turns(player, 1, 100)
    assert player.hp == player.max_hp
    assert player.mp == player.max_mp


def test_recover_mp_on_descend():
    player = new_player(mp=0)
    amount = recover_mp_on_descend(player, SURVIVAL)
    assert amount == int(player.max_mp * SURVIVAL.descend_mp_recover_ratio)
    assert player.mp == amount
    full = new_player()
    assert recover_mp_on_descend(full, SURVIVAL) == 0
