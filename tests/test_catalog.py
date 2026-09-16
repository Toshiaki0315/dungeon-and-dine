import copy

import pytest

from game import data_loader
from game.systems.catalog import Catalog

DATA = data_loader.load_all()


def test_catalog_loads_all_definitions():
    catalog = Catalog.from_data(DATA)
    assert len(catalog.monsters) == 25  # 通常20種 + 20階ごとのボス5体
    assert {"knife", "spear", "whip", "bow", "katana"} <= set(catalog.items)
    assert len(catalog.traps) == 7
    assert len(catalog.skills) == 7


def test_every_floor_has_monsters_within_their_floor_range():
    catalog = Catalog.from_data(DATA)
    for floor_number in range(1, 21):
        table = catalog.spawn_table(floor_number)
        assert table, f"B{floor_number}F に出現する敵がいない"
        for monster_id in table:
            monster = catalog.monsters[monster_id]
            assert monster.first_floor <= floor_number <= monster.last_floor


def test_spec_values_for_monsters():
    rat = Catalog.from_data(DATA).monsters["giant_rat"]
    # 経験値はフェーズ7で調整した（仕様書 8.2 の【仮】値は 3）
    assert (rat.hp, rat.atk, rat.defense, rat.speed, rat.ai) == (10, 4, 1, 100, "chase")
    assert rat.exp == 5


def test_skills_are_learned_at_spec_levels():
    skills = Catalog.from_data(DATA).skills
    levels = {s.name: (s.level, s.mp) for s in skills.values()}
    assert levels == {
        "解体術": (1, 3),
        "強撃": (3, 4),
        "薙ぎ払い": (6, 6),
        "目利き": (9, 8),
        "忍び足": (12, 8),
        "火起こし": (15, 12),
        "捨て身の一撃": (20, 15),
    }


def test_unknown_status_reference_is_rejected():
    data = copy.deepcopy(DATA)
    data["enemies"]["enemies"][0]["abilities"] = [
        {"type": "on_hit_status", "status": "petrify", "chance": 10}
    ]
    with pytest.raises(data_loader.DataValidationError, match="petrify"):
        Catalog.from_data(data)


def test_spawn_table_outside_monster_floor_range_is_rejected():
    data = copy.deepcopy(DATA)
    data["floors"]["floors"][0]["monsters"]["labyrinth_hound"] = 5
    with pytest.raises(data_loader.DataValidationError, match="labyrinth_hound"):
        Catalog.from_data(data)


def test_duplicate_id_is_rejected():
    data = copy.deepcopy(DATA)
    data["traps"]["traps"].append(dict(data["traps"]["traps"][0]))
    with pytest.raises(data_loader.DataValidationError, match="重複"):
        Catalog.from_data(data)
