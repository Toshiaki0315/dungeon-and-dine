import random

from game import data_loader
from game.entities.item import ItemInstance
from game.systems.catalog import Catalog
from game.systems.equipment import (
    EquipmentParams,
    compute_bonus,
    describe_equipment,
    generate_equipment,
)

DATA = data_loader.load_all()
CATALOG = Catalog.from_data(DATA)
PARAMS = EquipmentParams.from_dict(DATA["balance"]["equipment"])
TRAITS = {t.id: t for t in PARAMS.marks + PARAMS.curses}


def make(item_id, **changes):
    return ItemInstance(CATALOG.items[item_id], **changes)


def test_generated_equipment_is_unidentified_and_within_ranges():
    spear = CATALOG.items["spear"]
    for seed in range(500):
        item = generate_equipment(spear, random.Random(seed), 1, PARAMS)
        assert not item.identified and not item.curse_known
        if item.cursed:
            assert PARAMS.cursed_modifier_min <= item.modifier <= PARAMS.cursed_modifier_max
        else:
            assert min(PARAMS.modifier_weights) <= item.modifier <= max(PARAMS.modifier_weights)


def test_curse_chance_is_higher_on_deep_floors():
    armor = CATALOG.items["leather_armor"]
    rng = random.Random(0)
    shallow = sum(generate_equipment(armor, rng, 1, PARAMS).cursed for _ in range(4000)) / 4000
    deep = (
        sum(
            generate_equipment(armor, rng, PARAMS.deep_curse_floor, PARAMS).cursed
            for _ in range(4000)
        )
        / 4000
    )
    assert abs(shallow - PARAMS.curse_chance / 100) < 0.03
    assert abs(deep - PARAMS.deep_curse_chance / 100) < 0.03


def test_names_hide_unidentified_details():
    assert make("spear", modifier=2, identified=False, curse_known=False).name == "？の槍"
    assert make("spear", modifier=2).name == "槍+2"
    assert make("spear", modifier=-1, mark=TRAITS["fire"]).name == "槍-1〔炎〕"
    assert make("spear").name == "槍"
    assert make("arrow", count=12).name == "矢（12本）"


def test_description_shows_question_marks_for_unknown_values():
    hidden = make("spear", modifier=3, mark=TRAITS["fire"], identified=False, curse_known=False)
    lines = describe_equipment(hidden)
    text = "\n".join(lines)
    assert "???" in text
    assert "+3" not in text and "炎" not in text

    appraised = make("spear", modifier=3, curse=TRAITS["skill_seal"], identified=False)
    assert "呪い あり" in describe_equipment(appraised)
    assert "スキル封じ" not in "\n".join(describe_equipment(appraised))

    known = make("spear", modifier=3, mark=TRAITS["fire"])
    assert describe_equipment(known) == ["武器  攻撃力 4", "修正値 +3  印 炎", "呪い なし"]


def test_compute_bonus_sums_armor_marks_and_curses():
    equipment = {
        "weapon": make("katana", mark=TRAITS["critical"]),
        "shield": make("wooden_shield", modifier=1),
        "helmet": make("iron_helm", curse=TRAITS["sight"]),
        "armor": make("leather_armor"),
        "shoes": make("sandals", mark=TRAITS["filling"]),
    }
    bonus = compute_bonus(equipment)
    assert bonus.defense == (2 + 1) + 2 + 3 + 0
    assert bonus.crit_bonus == 10
    assert bonus.block_rate == 15
    assert bonus.status_resist
    assert bonus.sight_bonus == -1
    assert bonus.max_hp_bonus == 5
    assert bonus.trap_find_bonus == 20
    assert bonus.hunger_rate_percent == 64  # 草履 0.8 × 腹持ち 0.8


def test_curse_effects_in_bonus():
    bonus = compute_bonus(
        {
            "weapon": make("spear", curse=TRAITS["half_hit"]),
            "armor": make("chain_mail", curse=TRAITS["hunger"]),
            "shoes": make("iron_boots", curse=TRAITS["trap_blind"]),
            "helmet": make("leather_cap", curse=TRAITS["skill_seal"]),
            "shield": make("iron_shield", curse=TRAITS["cooking"]),
        }
    )
    assert bonus.hit_percent == 50
    assert bonus.hunger_rate_percent == 160  # 鉄の靴 0.8 × 呪い 2
    assert bonus.no_trap_find
    assert bonus.skill_seal
    assert bonus.cook_fail_bonus == 30
    assert bonus.trap_avoid_rate == 20
