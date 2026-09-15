import pytest

from game import data_loader
from game.systems.catalog import Catalog
from game.systems.combat import (
    REACH_AROUND,
    REACH_FAN,
    REACH_FRONT,
    REACH_LINE,
    REACH_PIERCE,
    CombatParams,
    CombatStats,
    hit_chance,
    reach_cells,
    roll_attack,
    round_half_up,
)
from game.world.direction import Direction
from tests.helpers import FixedRng, make_floor

DATA = data_loader.load_all()
PARAMS = CombatParams.from_dict(DATA["balance"]["combat"])
CATALOG = Catalog.from_data(DATA)

OPEN = make_floor(
    [
        "#########",
        "#.......#",
        "#.......#",
        "#.......#",
        "#.......#",
        "#.......#",
        "#########",
    ]
)


def stats(atk=10, defense=0, hit=85, evade=0, crit_rate=5):
    return CombatStats(atk=atk, defense=defense, hit=hit, evade=evade, crit_rate=crit_rate)


def test_round_half_up():
    assert [round_half_up(v) for v in (0.5, 1.5, 2.4, 2.5)] == [1, 2, 2, 3]


def test_hit_chance_is_clamped():
    assert hit_chance(stats(hit=90), stats(evade=5), PARAMS) == 85
    assert hit_chance(stats(hit=200), stats(), PARAMS) == PARAMS.hit_max
    assert hit_chance(stats(hit=0), stats(evade=50), PARAMS) == PARAMS.hit_min


def test_damage_formula():
    # 10 × 1.0 − 4 × 0.5 = 8
    result = roll_attack(stats(atk=10), stats(defense=4), FixedRng(50), PARAMS)
    assert result == result.__class__(hit=True, damage=8, critical=False)


def test_critical_multiplies_damage():
    result = roll_attack(stats(atk=10), stats(defense=4), FixedRng(0), PARAMS)
    assert result.critical
    assert result.damage == round_half_up(8 * PARAMS.crit_multiplier)


def test_skill_multiplier_and_halving():
    assert roll_attack(stats(), stats(defense=4), FixedRng(50), PARAMS, multiplier=1.8).damage == 14
    assert roll_attack(stats(), stats(defense=4), FixedRng(50), PARAMS, halve=True).damage == 4


def test_damage_is_at_least_one():
    assert roll_attack(stats(atk=1), stats(defense=30), FixedRng(50), PARAMS).damage == 1


def test_miss_when_roll_exceeds_hit_chance():
    assert not roll_attack(stats(hit=50), stats(), FixedRng(99), PARAMS).hit


# --- 武器ごとの攻撃範囲（仕様書 10.2） ---


def weapon_cells(weapon_id, x, y, facing, floor=OPEN):
    weapon = CATALOG.items[weapon_id].weapon
    return reach_cells(floor, x, y, facing, weapon.reach, weapon.length)


def test_unarmed_knife_and_katana_hit_front_one_cell():
    unarmed = CATALOG.unarmed
    assert reach_cells(OPEN, 4, 3, Direction.RIGHT, unarmed.reach, unarmed.length) == [(5, 3)]
    assert weapon_cells("knife", 4, 3, Direction.UP_LEFT) == [(3, 2)]
    assert weapon_cells("katana", 4, 3, Direction.DOWN) == [(4, 4)]


def test_spear_pierces_two_cells():
    assert weapon_cells("spear", 4, 3, Direction.RIGHT) == [(5, 3), (6, 3)]
    assert weapon_cells("spear", 4, 3, Direction.DOWN_LEFT) == [(3, 4), (2, 5)]


def test_spear_is_blocked_by_wall():
    floor = make_floor(["#####", "#.#.#", "#####"])
    assert weapon_cells("spear", 1, 1, Direction.RIGHT, floor) == []


def test_whip_hits_front_fan_of_three():
    assert set(weapon_cells("whip", 4, 3, Direction.RIGHT)) == {(5, 3), (5, 2), (5, 4)}
    # 斜め向きでは正面を基準に左右へ45度
    assert set(weapon_cells("whip", 4, 3, Direction.UP_RIGHT)) == {(5, 2), (4, 2), (5, 3)}


def test_whip_fan_respects_corner_rule():
    floor = make_floor(["#####", "#.#.#", "#...#", "#####"])
    # (1,2) から右向き: 右上 (2,1) は壁、右下はマップ外の壁
    assert weapon_cells("whip", 1, 2, Direction.RIGHT, floor) == [(2, 2)]


def test_bow_reaches_eight_cells_until_wall():
    wide = make_floor(["############", "#..........#", "############"])
    weapon = CATALOG.items["bow"].weapon
    assert weapon.uses_arrows
    cells = reach_cells(wide, 1, 1, Direction.RIGHT, weapon.reach, weapon.length)
    assert cells == [(x, 1) for x in range(2, 10)]
    assert weapon_cells("bow", 1, 3, Direction.RIGHT) == [(x, 3) for x in range(2, 8)]


@pytest.mark.parametrize(
    ("skill_id", "expected"),
    [
        ("butcher", [(5, 3)]),
        ("power_strike", [(5, 3)]),
        ("reckless_blow", [(5, 3)]),
        ("sweep", [(4 + d.dx, 3 + d.dy) for d in Direction]),
    ],
)
def test_attack_skill_areas(skill_id, expected):
    skill = CATALOG.skills[skill_id]
    assert set(reach_cells(OPEN, 4, 3, Direction.RIGHT, skill.area)) == set(expected)


def test_all_reach_types_are_supported():
    for reach in (REACH_FRONT, REACH_PIERCE, REACH_LINE, REACH_FAN, REACH_AROUND):
        reach_cells(OPEN, 4, 3, Direction.UP, reach, 2)
    with pytest.raises(ValueError):
        reach_cells(OPEN, 4, 3, Direction.UP, "unknown")
