"""食材ドロップ・腐敗・調理・焚き火（フェーズ5）のゲーム状態のテスト。"""

from game.entities.item import ItemInstance
from game.entities.monster import MODE_CHASE
from game.systems import spawn
from game.systems.cooking import HEAT_CAMPFIRE, HEAT_STOVE
from game.systems.game_state import GameState
from game.world.direction import Direction
from game.world.floor import Campfire
from tests.helpers import FixedRng, make_floor
from tests.test_game_state import CATALOG, PARAMS, log_text, new_state, place_monster, wait_turns

COOKING = PARAMS.cooking
FIRE_MARK = next(m for m in PARAMS.equipment.marks if m.id == "fire")
COOK_CURSE = next(c for c in PARAMS.equipment.curses if c.id == "cooking")


def give(state, item_id, **changes):
    item = ItemInstance(CATALOG.items[item_id], **changes)
    assert state.inventory.add(item)
    return item


def kill_in_front(state, monster_id="giant_rat"):
    """目の前の敵を通常攻撃で倒す。"""
    state.face(Direction.RIGHT)
    place_monster(state, monster_id, hp=1)
    state.attack()


def floor_item_ids(state):
    return [floor_item.item.id for floor_item in state.floor.items]


def light_campfire(state, direction=Direction.UP):
    """プレイヤーの隣に焚き火を置く（安全地帯に入る）。"""
    p = state.player
    campfire = Campfire(p.x + direction.dx, p.y + direction.dy)
    state.floor.campfires.append(campfire)
    return campfire


# --- 食材のドロップ（仕様書 9.1） ---


def test_defeated_monster_drops_its_ingredient():
    state = new_state(rng_roll=0)  # ドロップ判定に必ず成功する
    kill_in_front(state)
    assert "rat_meat" in floor_item_ids(state)


def test_drop_chance_is_higher_with_a_knife():
    state = new_state(rng_roll=40)  # 基本30%では落とさず、ナイフの45%なら落とす出目
    kill_in_front(state)
    assert "rat_meat" not in floor_item_ids(state)

    state = new_state(rng_roll=40)
    state.equip(give(state, "knife"))
    kill_in_front(state)
    assert "rat_meat" in floor_item_ids(state)


def test_butchering_skill_always_drops_an_ingredient():
    state = new_state(rng_roll=50)  # 攻撃は当たるが、確率では食材を落とさない出目
    state.face(Direction.RIGHT)
    place_monster(state, "giant_rat", hp=1)
    assert state.use_skill("butcher") is True
    assert "rat_meat" in floor_item_ids(state)


def test_fire_attack_drops_grilled_ingredient():
    state = new_state(rng_roll=0)
    knife = ItemInstance(CATALOG.items["knife"], mark=FIRE_MARK)
    state.inventory.add(knife)
    state.equip(knife)
    kill_in_front(state)
    assert "grilled_rat_meat" in floor_item_ids(state)
    assert "rat_meat" not in floor_item_ids(state)


# --- 腐敗（仕様書 9.1） ---


def test_raw_meat_rots_after_a_while():
    state = new_state()
    meat = state.new_item(CATALOG.items["rat_meat"])
    assert meat.rot_at == state.turn + COOKING.rot_turns
    assert state.inventory.add(meat)
    meat.rot_at = state.turn + 2
    wait_turns(state, 2)
    assert [i.id for i in state.inventory.items] == ["rotten_meat"]
    assert "腐ってしまった" in log_text(state)


def test_grilled_ingredients_do_not_rot():
    state = new_state()
    grilled = state.new_item(CATALOG.items["grilled_rat_meat"])
    assert grilled.rot_at is None
    state.inventory.add(grilled)
    wait_turns(state, 5)
    assert [i.id for i in state.inventory.items] == ["grilled_rat_meat"]


def test_eating_raw_meat_fills_and_may_poison():
    state = new_state(rng_roll=0)  # 30% の毒判定に当たる出目
    state.player.satiety = 50
    state.use_item(give(state, "rat_meat"))
    assert state.player.satiety == 60
    assert "poison" in state.player.statuses

    state = new_state(rng_roll=50)  # 毒にならない出目
    state.use_item(give(state, "rat_meat"))
    assert "poison" not in state.player.statuses


def test_eating_the_mystery_object_causes_one_penalty():
    state = new_state(rng_roll=0)
    state.player.satiety = 50
    state.use_item(give(state, "mystery_food"))
    ailments = {"poison", "confusion", "max_hp_down"}
    assert state.player.satiety == 50 or any(a in state.player.statuses for a in ailments)


# --- 調理できる状況（仕様書 9.3） ---


def test_campfire_nearby_allows_cooking():
    state = new_state()
    assert state.can_cook is False
    light_campfire(state)
    assert state.heat_source() == HEAT_CAMPFIRE
    assert state.can_cook is True


def test_stove_works_only_when_no_enemy_is_in_sight():
    state = new_state()
    give(state, "stove")
    assert state.heat_source() == HEAT_STOVE
    place_monster(state, "giant_rat")
    assert state.heat_source() is None
    assert "コンロ" in state.cooking_unavailable_reason()


def test_equipped_items_cannot_be_used_as_materials():
    state = new_state()
    light_campfire(state)
    knife = give(state, "knife")
    state.equip(knife)
    assert knife not in state.cooking_candidates()


# --- 調理（仕様書 9.3 / 9.4） ---


def cooking_state(rng_roll=50):
    """焚き火のそばで、ネズミ肉と薬草を持っている状態。"""
    state = new_state(rng_roll=rng_roll)
    light_campfire(state)
    return state, give(state, "rat_meat"), give(state, "herb")


def test_cooking_takes_exactly_one_turn_and_makes_the_dish():
    state, meat, herb = cooking_state()
    plan = state.plan_cooking([meat, herb])
    assert plan is not None and plan.success is True
    assert state.turn == 0  # 材料を選んだだけではターンが進まない
    assert state.inventory.items == [meat, herb]

    assert state.apply_cooking(plan) is True
    assert state.turn == 1
    assert [i.id for i in state.inventory.items] == ["rat_skewer"]
    assert state.notebook.is_discovered("rat_skewer")
    assert "ネズミ肉の串焼き" in log_text(state)


def test_cancelling_the_selection_does_not_consume_a_turn():
    state, meat, herb = cooking_state()
    state.plan_cooking([meat, herb])
    assert state.turn == 0 and len(state.inventory.items) == 2


def test_unknown_combination_makes_the_mystery_object_and_is_recorded():
    state = new_state()
    light_campfire(state)
    herbs = give(state, "herb", count=2)  # 1枠にまとめた薬草から2つ使う
    plan = state.plan_cooking([herbs, herbs])
    assert plan is not None and plan.matched is None and plan.success is False
    state.apply_cooking(plan)
    assert [i.id for i in state.inventory.items] == ["mystery_food"]
    assert state.notebook.is_failure(("herb", "herb"))
    assert not state.notebook.discovered


def test_cooking_needs_two_or_three_materials():
    state, meat, herb = cooking_state()
    assert state.plan_cooking([meat]) is None
    assert state.plan_cooking([meat, meat]) is None  # 同じ個体は1回しか使えない


def test_curse_raises_the_failure_rate():
    state, meat, herb = cooking_state(rng_roll=30)  # 基本5%では成功し、呪いの35%では失敗する出目
    plan = state.plan_cooking([meat, herb])
    assert plan is not None and plan.success is True

    cursed_knife = ItemInstance(CATALOG.items["knife"], curse=COOK_CURSE)
    state.inventory.add(cursed_knife)
    state.equip(cursed_knife, confirmed=True)
    plan = state.plan_cooking([meat, herb])
    assert plan is not None and plan.matched is not None and plan.success is False


def test_stove_is_consumed_and_breaks():
    state = new_state()
    stove = give(state, "stove")
    assert stove.charges == 3
    for remaining in (2, 1, 0):
        meat, herb = give(state, "rat_meat"), give(state, "herb")
        plan = state.plan_cooking([meat, herb])
        assert plan is not None and plan.heat == HEAT_STOVE
        state.apply_cooking(plan)
        assert stove.charges == remaining
    assert stove not in state.inventory.items
    assert "壊れてしまった" in log_text(state)


# --- 焚き火・安全地帯（仕様書 9.3） ---


def test_kindle_skill_makes_a_temporary_campfire():
    state = new_state()
    state.player.skills.append("kindle")
    state.player.mp = 30
    state.face(Direction.RIGHT)
    assert state.use_skill("kindle") is True
    duration = CATALOG.skills["kindle"].duration
    assert len(state.floor.campfires) == 1

    assert state.use_skill("kindle") is False  # 1つの階につき1回まで
    assert "もう火を起こせない" in log_text(state)

    wait_turns(state, duration)
    assert state.floor.campfires == []
    assert "焚き火が消えた" in log_text(state)


def test_monsters_never_enter_the_safe_zone():
    state = new_state()
    light_campfire(state, Direction.DOWN)
    monster = place_monster(state, "giant_rat", Direction.RIGHT, distance=4, mode=MODE_CHASE)
    for _ in range(12):
        state.wait()
        assert not state.floor.in_safe_zone(*monster.pos)


def test_monsters_do_not_respawn_in_the_safe_zone():
    floor = make_floor(["#####", "#...#", "#...#", "#####"])
    floor.campfires.append(Campfire(2, 2))
    rng = FixedRng()
    assert spawn.respawn_monster(floor, rng, CATALOG, lambda c: True, lambda: 1) is None


def test_campfires_are_placed_on_the_guaranteed_floors():
    state = GameState(42, PARAMS)
    state.enter_floor(COOKING.campfire_floors[0])
    assert state.floor.campfires


# --- 先人のメモ（仕様書 9.6） ---


def test_memo_registers_an_unknown_recipe():
    state = new_state()
    state.use_item(give(state, "memo"))
    assert len(state.notebook.discovered) == 1
    assert "書き写した" in log_text(state)


def test_memo_gives_gold_when_every_recipe_is_known():
    state = new_state()
    for recipe_id in CATALOG.recipes:
        state.notebook.discover(recipe_id)
    state.use_item(give(state, "memo"))
    assert state.player.gold == COOKING.memo_gold


def test_a_stack_can_only_provide_as_many_materials_as_it_holds():
    state = new_state()
    light_campfire(state)
    herbs = give(state, "herb", count=2)
    assert state.plan_cooking([herbs, herbs, herbs]) is None
    assert state.plan_cooking([herbs, herbs]) is not None


def test_a_stack_of_raw_meat_rots_together():
    state = new_state()
    meat = give(state, "rat_meat", count=3, rot_at=state.turn + 1)
    state.wait()
    state.wait()
    assert [(i.id, i.count) for i in state.inventory.items] == [("rotten_meat", 3)]
    assert meat not in state.inventory.items
