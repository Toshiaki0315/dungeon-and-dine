"""装備・呪い・鑑定・宝箱（フェーズ4）のゲーム状態のテスト。"""

from game.entities.item import Chest, ItemInstance
from game.entities.monster import MODE_CHASE
from game.systems.game_state import EFFECT_CURSE, EquipResult, GameState, MoveResult
from game.world.direction import Direction
from tests.helpers import FixedRng
from tests.test_game_state import (
    CATALOG,
    PARAMS,
    SURVIVAL,
    log_text,
    new_state,
    place_monster,
    place_trap,
    wait_turns,
)

TRAITS = {t.id: t for t in PARAMS.equipment.marks + PARAMS.equipment.curses}


def give(state, item_id, *, identified=True, **changes):
    item = ItemInstance(
        CATALOG.items[item_id], identified=identified, curse_known=identified, **changes
    )
    assert state.inventory.add(item)
    return item


# --- 装備 ---


def test_equip_weapon_raises_attack_and_consumes_turn():
    state = new_state()
    base = state.player_combat_stats().atk
    spear = give(state, "spear", modifier=2)
    assert state.equip(spear) == EquipResult.EQUIPPED
    assert state.player.weapon is spear
    assert state.player_combat_stats().atk == base + 4 + 2
    assert state.turn == 1


def test_armor_adds_defense_and_max_hp_until_removed():
    state = new_state()
    armor = give(state, "chain_mail", modifier=1)
    state.equip(armor)
    assert state.player_combat_stats().defense == PARAMS.player.defense + 5 + 1
    assert state.player.max_hp == PARAMS.player.hp + 10
    state.player.hp = state.player.max_hp
    assert state.unequip(armor) == EquipResult.UNEQUIPPED
    assert state.player.max_hp == PARAMS.player.hp
    assert state.player.hp == PARAMS.player.hp


def test_unidentified_equipment_needs_confirmation_and_is_identified_by_equipping():
    state = new_state()
    katana = give(state, "katana", identified=False, modifier=3)
    assert state.equip(katana) == EquipResult.NEEDS_CONFIRM
    assert state.player.weapon is None and state.turn == 0
    assert state.equip(katana, confirmed=True) == EquipResult.EQUIPPED
    assert katana.identified
    assert "刀+3" in log_text(state)


def test_preview_does_not_reveal_unidentified_stats():
    state = new_state()
    hidden = give(state, "spear", identified=False, modifier=5)
    known = give(state, "spear", modifier=1)
    assert state.preview_stats("weapon", hidden) is None
    assert state.preview_stats("weapon", known).atk == state.player_combat_stats().atk + 5


def test_cursed_equipment_cannot_be_removed_dropped_or_replaced():
    state = new_state()
    armor = give(state, "leather_armor", identified=False, curse=TRAITS["skill_seal"], modifier=-2)
    state.equip(armor, confirmed=True)
    assert "呪われていた" in log_text(state)
    assert [e.kind for e in state.consume_events()] == [EFFECT_CURSE]
    assert state.unequip(armor) == EquipResult.FAILED
    assert not state.drop_item(armor)
    assert not state.throw_item(armor)
    other = give(state, "plate_armor")
    assert state.equip(other, confirmed=True) == EquipResult.FAILED
    assert state.player.equipment["armor"] is armor


def test_known_cursed_equipment_asks_for_confirmation():
    state = new_state()
    cursed = give(state, "spear", curse=TRAITS["half_hit"])
    assert state.equip(cursed) == EquipResult.NEEDS_CONFIRM


def test_skill_seal_curse_blocks_skills():
    state = new_state()
    helmet = give(state, "leather_cap", curse=TRAITS["skill_seal"])
    state.equip(helmet, confirmed=True)
    assert not state.use_skill("butcher")
    assert "スキルが使えない" in log_text(state)


def test_half_hit_curse_halves_hit_rate():
    state = new_state()
    spear = give(state, "spear", curse=TRAITS["half_hit"])
    state.equip(spear, confirmed=True)
    assert state.player_combat_stats().hit == PARAMS.player.hit // 2


def test_dropping_equipped_item_unequips_it():
    state = new_state()
    spear = give(state, "spear")
    state.equip(spear)
    assert state.drop_item(spear)
    assert state.player.weapon is None


# --- 解呪・鑑定 ---


def test_uncurse_scroll_removes_curses_of_equipped_items():
    state = new_state()
    armor = give(state, "leather_armor", curse=TRAITS["hunger"], modifier=-2)
    spare = give(state, "spear", curse=TRAITS["half_hit"])
    state.equip(armor, confirmed=True)
    scroll = give(state, "uncurse_scroll")
    assert state.item_targets(scroll) is None
    assert state.use_item(scroll)
    assert not armor.cursed
    assert armor.modifier == -2
    assert spare.cursed  # 装備していないものは解けない
    assert state.unequip(armor) == EquipResult.UNEQUIPPED


def test_holy_water_uncurses_one_item_and_raises_modifier():
    state = new_state()
    spear = give(state, "spear", identified=False, curse=TRAITS["half_hit"], modifier=-2)
    holy = give(state, "holy_water")
    assert spear in state.item_targets(holy)
    assert not state.use_item(holy)  # 対象を選ばないと使えない
    assert state.inventory.find("holy_water") is holy
    assert state.use_item(holy, spear)
    assert not spear.cursed and spear.curse_known
    assert spear.modifier == -1
    assert state.inventory.find("holy_water") is None


def test_loupe_identifies_target():
    state = new_state()
    loupe = give(state, "loupe")
    assert state.item_targets(loupe) == []
    spear = give(state, "spear", identified=False, modifier=4, mark=TRAITS["sturdy"])
    assert state.use_item(loupe, spear)
    assert spear.identified and spear.curse_known
    assert "槍+4〔頑丈〕" in log_text(state)


def test_appraise_skill_reveals_only_curse():
    state = new_state()
    state.player.skills.append("appraise")
    spear = give(state, "spear", identified=False, curse=TRAITS["sight"])
    assert state.skill_targets("appraise") == [spear]
    assert state.use_skill("appraise", spear)
    assert spear.curse_known and not spear.identified
    assert state.player.mp == PARAMS.player.mp - CATALOG.skills["appraise"].mp
    assert "呪われている" in log_text(state)
    assert state.skill_targets("appraise") == []


# --- 防具の効果 ---


def test_shield_blocks_attacks():
    state = new_state(rng_roll=10)  # 命中するが盾（15%）で防ぐ出目
    shield = give(state, "wooden_shield")
    state.equip(shield)
    place_monster(state, "giant_rat", mode=MODE_CHASE)
    wait_turns(state, 3)
    assert state.player.hp == PARAMS.player.hp
    assert "盾で防いだ" in log_text(state)


def test_shoes_reduce_hunger_and_help_find_traps():
    state = new_state(rng_roll=25)
    sandals = give(state, "sandals")
    state.equip(sandals)
    trap = place_trap(state, "alarm", Direction.UP)
    state.wait()
    assert trap.discovered  # 10% + 20% > 出目25
    wait_turns(state, 48)
    turns = state.turn
    assert state.player.satiety == PARAMS.player.satiety - (turns * 80) // (
        SURVIVAL.satiety_decay_interval * 100
    )


def test_helmet_halves_status_chance():
    state = new_state(rng_roll=60)
    helm = give(state, "iron_helm")
    state.equip(helm)
    place_trap(state, "sleep_gas")
    state.move_player(Direction.RIGHT)
    assert "sleep" not in state.player.statuses


def test_rust_trap_lowers_modifier_unless_sturdy():
    state = new_state()
    spear = give(state, "spear", modifier=1)
    state.equip(spear)
    place_trap(state, "rust")
    state.move_player(Direction.RIGHT)
    assert spear.modifier == 0

    state = new_state()
    sturdy = give(state, "spear", modifier=1, mark=TRAITS["sturdy"])
    state.equip(sturdy)
    place_trap(state, "rust")
    state.move_player(Direction.RIGHT)
    assert sturdy.modifier == 1


# --- 宝箱・ミミック ---


def place_chest(state, contents_id, direction=Direction.RIGHT, **kwargs):
    p = state.player
    chest = Chest(
        ItemInstance(CATALOG.items[contents_id]), p.x + direction.dx, p.y + direction.dy, **kwargs
    )
    state.floor.chests.append(chest)
    return chest


def test_moving_into_chest_opens_it():
    state = new_state()
    chest = place_chest(state, "herb")
    assert state.move_player(Direction.RIGHT) == MoveResult.OPENED
    assert chest.opened
    assert state.inventory.find("herb") is chest.contents
    assert state.turn == 1
    assert state.move_player(Direction.RIGHT) == MoveResult.BLOCKED
    assert state.turn == 1


def test_attack_key_opens_chest_in_front():
    state = new_state()
    chest = place_chest(state, "ration", Direction.DOWN)
    state.player.facing = Direction.DOWN
    state.attack()
    assert chest.opened


def test_trapped_chest_triggers_a_trap():
    state = new_state()
    place_chest(state, "herb", trapped=True)
    state.move_player(Direction.RIGHT)
    assert "仕掛けられていた" in log_text(state)


def test_monsters_cannot_walk_through_chests():
    state = new_state()
    chest = place_chest(state, "herb")
    assert not state.is_free_for_monster(*chest.pos)


def test_mimic_drops_chest_contents():
    state = new_state(rng_roll=50)
    state.player.facing = Direction.RIGHT
    mimic = place_monster(state, "mimic", hp=1)
    assert mimic.disguised
    state.attack()
    assert mimic not in state.floor.monsters
    assert len(state.floor.items) >= 1


def test_generated_floors_have_chests_and_unidentified_equipment():
    found_equipment = False
    for seed in range(10):
        state = GameState(seed, PARAMS)
        spawn = PARAMS.spawn
        assert spawn.chests_min <= len(state.floor.chests) <= spawn.chests_max
        items = [fi.item for fi in state.floor.items] + [c.contents for c in state.floor.chests]
        for item in items:
            if item.is_equipment:
                found_equipment = True
                assert not item.identified
    assert found_equipment


def test_rng_roll_helper_is_used(monkeypatch):
    # FixedRng を使ったテストが意図どおり動くことの確認
    assert FixedRng(10).randrange(100) == 10
