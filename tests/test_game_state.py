from dataclasses import replace

from game import data_loader
from game.entities.item import FloorItem, ItemInstance
from game.entities.monster import MODE_CHASE, Monster
from game.systems.game_state import GameParams, GameState, MoveResult
from game.systems.inventory import Inventory
from game.systems.message_log import strip_markup
from game.systems.meta import Loadout
from game.systems.progression import exp_to_next_level
from game.systems.traps import Trap
from game.world.direction import Direction
from game.world.fov import Visibility
from tests.helpers import FixedRng

PARAMS = GameParams.from_data(data_loader.load_all())
# 途中で敵が追加出現しないようにしたパラメータ
QUIET = replace(PARAMS, spawn=replace(PARAMS.spawn, respawn_interval=10**9))
SURVIVAL = PARAMS.survival
CATALOG = PARAMS.catalog


def new_state(seed=42, *, params=QUIET, empty=True, rng_roll=None):
    """テスト用の状態。empty なら敵・アイテム・罠を取り除き、プレイヤーを最初の部屋の中央に置く。"""
    state = GameState(seed, params)
    if empty:
        state.floor.monsters.clear()
        state.floor.items.clear()
        state.floor.traps.clear()
        room = state.floor.room_at(*state.player.pos)
        state.player.x, state.player.y = room.center
        state.update_fov()
    if rng_roll is not None:
        state.rng = FixedRng(rng_roll)
    return state


def place_monster(state, monster_id, direction=Direction.RIGHT, distance=1, **changes):
    p = state.player
    monster = Monster.spawn(
        CATALOG.monsters[monster_id],
        p.x + direction.dx * distance,
        p.y + direction.dy * distance,
        uid=1000 + len(state.floor.monsters),
    )
    for key, value in changes.items():
        setattr(monster, key, value)
    state.floor.monsters.append(monster)
    state.update_fov()
    return monster


def place_item(state, item_id, direction=Direction.RIGHT, count=1):
    p = state.player
    item = ItemInstance(CATALOG.items[item_id], count)
    state.floor.items.append(FloorItem(item, p.x + direction.dx, p.y + direction.dy))
    return item


def place_trap(state, trap_id, direction=Direction.RIGHT, discovered=False):
    p = state.player
    trap = Trap(CATALOG.traps[trap_id], p.x + direction.dx, p.y + direction.dy, discovered)
    state.floor.traps.append(trap)
    return trap


def log_text(state):
    return "\n".join(strip_markup(e) for e in state.log.entries)


def wait_turns(state, count):
    for _ in range(count):
        state.wait()


# --- 基本 ---


def test_new_run_starts_on_b1f_with_initial_stats_and_skill():
    state = GameState(42, PARAMS)
    assert state.floor.number == 1
    assert state.area.name == "苔むす洞窟"
    assert state.turn == 0
    assert state.player.pos == state.floor.start
    assert state.player.hp == state.player.max_hp == PARAMS.player.hp
    assert state.player.skills == ["butcher"]
    assert len(state.inventory) == 0


def test_monsters_items_and_traps_are_placed_by_data():
    state = GameState(42, PARAMS)
    spawn = PARAMS.spawn
    floor = state.floor
    assert spawn.monsters_min <= len(floor.monsters) <= spawn.monsters_max
    assert spawn.items_min <= len(floor.items) <= spawn.items_max
    assert spawn.traps_min <= len(floor.traps) <= spawn.traps_max
    start_room = floor.room_at(*floor.start)
    for monster in floor.monsters:
        assert monster.definition.id in CATALOG.spawn_table(1)
        assert not start_room.contains(*monster.pos)
    assert all(not trap.discovered for trap in floor.traps)


def test_move_consumes_one_turn_and_face_does_not():
    state = new_state()
    state.face(Direction.LEFT)
    assert state.turn == 0
    assert state.move_player(Direction.RIGHT) == MoveResult.MOVED
    assert state.turn == 1


def test_blocked_move_does_not_consume_turn():
    state = new_state()
    room = state.floor.room_at(*state.player.pos)
    state.player.x, state.player.y = room.x, room.y
    assert state.move_player(Direction.UP_LEFT) == MoveResult.BLOCKED
    assert state.turn == 0
    assert state.player.facing == Direction.UP_LEFT


# --- 満腹度・階層・視界（フェーズ2） ---


def test_satiety_decreases_as_turns_pass():
    state = new_state()
    interval = SURVIVAL.satiety_decay_interval
    wait_turns(state, interval - 1)
    assert state.player.satiety == PARAMS.player.satiety
    wait_turns(state, 1 + interval * 9)
    assert state.player.satiety == PARAMS.player.satiety - 10


def test_starvation_leads_to_game_over():
    state = new_state()
    state.player.satiety = 0
    state.player.hp = 2
    wait_turns(state, 2)
    assert state.is_game_over
    assert "力尽きた" in state.log.latest(1)[0]
    turn = state.turn
    state.wait()
    assert state.move_player(Direction.RIGHT) == MoveResult.BLOCKED
    assert state.turn == turn


def test_descend_generates_next_floor():
    state = new_state()
    assert not state.descend()
    state.player.x, state.player.y = state.floor.stairs
    state.player.mp = 0
    assert state.descend()
    assert state.floor.number == 2
    assert state.player.pos == state.floor.start
    assert state.player.mp == int(PARAMS.player.mp * SURVIVAL.descend_mp_recover_ratio)
    room = state.floor.room_at(*state.player.pos)
    assert all(state.fog.state(*cell) == Visibility.VISIBLE for cell in room.cells())


def test_can_keep_descending_past_the_boss_floor():
    """迷宮に最下層はない。ボス階より下へも潜り続けられる。"""
    state = new_state()
    state.enter_floor(PARAMS.boss_interval + 1)
    state.player.x, state.player.y = state.floor.stairs
    assert state.descend() is True
    assert state.floor.number == PARAMS.boss_interval + 2


# --- 戦闘 ---


def test_moving_into_monster_attacks_and_kill_gives_exp():
    state = new_state(rng_roll=50)
    rat = place_monster(state, "giant_rat", hp=1)
    assert state.move_player(Direction.RIGHT) == MoveResult.ATTACKED
    assert rat not in state.floor.monsters
    assert state.player.exp == rat.definition.exp
    assert state.turn == 1
    assert "巨大ネズミを倒した" in log_text(state)


def test_level_up_learns_skill():
    state = new_state(rng_roll=50)
    progression = PARAMS.progression
    state.player.level = 2
    state.player.exp = exp_to_next_level(2, progression) - 1
    state.player.facing = Direction.RIGHT
    place_monster(state, "giant_rat", hp=1)
    state.attack()
    assert state.player.level == 3
    assert "power_strike" in state.player.skills
    assert state.player.max_hp == PARAMS.player.hp + progression.hp_per_level


def test_monster_attacks_adjacent_player():
    state = new_state(rng_roll=50)
    place_monster(state, "giant_rat", mode=MODE_CHASE)
    state.wait()
    assert state.player.hp < PARAMS.player.hp
    assert "巨大ネズミの攻撃" in log_text(state)


def test_monster_on_hit_status():
    state = new_state(rng_roll=0)
    place_monster(state, "serpent", mode=MODE_CHASE, hp=999)
    state.wait()
    assert "poison" in state.player.statuses


def test_bow_uses_arrows_and_hits_first_monster_only():
    state = new_state(rng_roll=50)
    state.player.equipment["weapon"] = ItemInstance(CATALOG.items["bow"])
    state.inventory.add(ItemInstance(CATALOG.items["arrow"], 2))
    state.player.facing = Direction.RIGHT
    near = place_monster(state, "slime", hp=100)
    state.attack()
    assert state.inventory.items[0].count == 1
    assert near.hp < 100

    state.inventory.items.clear()
    assert state.effective_weapon() is CATALOG.unarmed


def test_attack_skill_consumes_mp_and_turn():
    state = new_state(rng_roll=50)
    state.player.facing = Direction.RIGHT
    rat = place_monster(state, "giant_rat", hp=100)
    assert state.use_skill("butcher")
    assert state.player.mp == PARAMS.player.mp - CATALOG.skills["butcher"].mp
    assert rat.hp < 100
    assert state.turn == 1


def test_skill_without_enough_mp_does_nothing():
    state = new_state()
    state.player.mp = 0
    assert not state.use_skill("butcher")
    assert state.turn == 0
    assert not state.use_skill("sweep")  # 未習得


def test_sweep_hits_all_around():
    state = new_state(rng_roll=50)
    state.player.skills.append("sweep")
    monsters = [place_monster(state, "slime", d, hp=100) for d in Direction]
    assert state.use_skill("sweep")
    assert all(m.hp < 100 for m in monsters)


# --- アイテム ---


def test_pick_up_item_when_stepping_on_it():
    state = new_state()
    herb = place_item(state, "herb")
    state.move_player(Direction.RIGHT)
    assert state.inventory.items == [herb]
    assert state.floor.items == []


def test_full_inventory_leaves_item_on_floor():
    state = new_state()
    for _ in range(state.inventory.capacity):
        state.inventory.add(ItemInstance(CATALOG.items["knife"]))  # 装備はまとめられない
    place_item(state, "ration")
    state.move_player(Direction.RIGHT)
    assert len(state.inventory) == state.inventory.capacity
    assert len(state.floor.items) == 1
    assert "持ちきれない" in log_text(state)


def test_gold_does_not_use_inventory_slot():
    state = new_state()
    place_item(state, "gold", count=30)
    state.move_player(Direction.RIGHT)
    assert state.player.gold == 30
    assert len(state.inventory) == 0


def test_use_herb_heals_and_consumes_turn():
    state = new_state()
    herb = ItemInstance(CATALOG.items["herb"])
    state.inventory.add(herb)
    state.player.hp = 1
    assert state.use_item(herb)
    assert state.player.hp == 31 or state.player.hp == state.player.max_hp
    assert len(state.inventory) == 0
    assert state.turn == 1


def test_unimplemented_item_is_not_consumed():
    state = new_state()
    loupe = ItemInstance(CATALOG.items["loupe"])
    state.inventory.add(loupe)
    assert not state.use_item(loupe)
    assert state.inventory.items == [loupe]
    assert state.turn == 0


def test_antidote_cures_poison():
    state = new_state()
    state.player.statuses.add(CATALOG.statuses["poison"])
    antidote = ItemInstance(CATALOG.items["antidote"])
    state.inventory.add(antidote)
    state.use_item(antidote)
    assert "poison" not in state.player.statuses


def test_fire_scroll_damages_monsters_around():
    state = new_state()
    near = place_monster(state, "slime", Direction.UP, hp=100)
    far = place_monster(state, "slime", Direction.DOWN, distance=2, hp=100)
    scroll = ItemInstance(CATALOG.items["fire_scroll"])
    state.inventory.add(scroll)
    state.use_item(scroll)
    assert near.hp == 100 - 15
    assert far.hp == 100


def test_throw_item_damages_first_monster():
    state = new_state()
    state.player.facing = Direction.RIGHT
    rat = place_monster(state, "giant_rat", hp=10)
    herb = ItemInstance(CATALOG.items["herb"])
    state.inventory.add(herb)
    assert state.throw_item(herb)
    assert rat.hp == 10 - PARAMS.combat.throw_damage
    assert len(state.inventory) == 0
    assert state.floor.items == []


def test_thrown_item_lands_on_floor_when_nothing_is_hit():
    state = new_state()
    state.player.facing = Direction.RIGHT
    herb = ItemInstance(CATALOG.items["herb"])
    state.inventory.add(herb)
    state.throw_item(herb)
    assert len(state.floor.items) == 1
    assert state.floor.items[0].x > state.player.x


def test_drop_item_at_feet():
    state = new_state()
    herb = ItemInstance(CATALOG.items["herb"])
    ration = ItemInstance(CATALOG.items["ration"])
    state.inventory.add(herb)
    state.inventory.add(ration)
    assert state.drop_item(herb)
    assert state.floor.item_at(*state.player.pos).item is herb
    assert not state.drop_item(ration)
    assert state.turn == 1


# --- 罠・状態異常 ---


def test_stepping_on_trap_triggers_and_reveals_it():
    state = new_state()
    trap = place_trap(state, "poison_arrow")
    state.move_player(Direction.RIGHT)
    assert trap.discovered
    assert "poison" in state.player.statuses
    assert state.player.hp <= PARAMS.player.hp - 3


def test_known_trap_asks_for_confirmation():
    state = new_state()
    place_trap(state, "hunger", discovered=True)
    assert state.move_player(Direction.RIGHT) == MoveResult.CONFIRM_TRAP
    assert state.turn == 0
    assert state.move_player(Direction.RIGHT, confirm_trap=True) == MoveResult.MOVED
    assert state.player.satiety == PARAMS.player.satiety - 20


def test_pit_trap_drops_to_next_floor():
    state = new_state()
    place_trap(state, "pit")
    state.move_player(Direction.RIGHT)
    assert state.floor.number == 2


def test_wait_searches_adjacent_traps():
    state = new_state(rng_roll=0)
    trap = place_trap(state, "alarm", Direction.DOWN_LEFT)
    state.wait()
    assert trap.discovered


def test_sleep_passes_turns_until_awake():
    state = new_state()
    state.player.statuses.add(CATALOG.statuses["sleep"])
    state.wait()
    assert "sleep" not in state.player.statuses
    assert state.turn == CATALOG.statuses["sleep"].duration


def test_poison_damages_each_turn_and_stops_regeneration():
    state = new_state()
    state.player.hp = 20
    state.player.statuses.add(CATALOG.statuses["poison"])
    wait_turns(state, SURVIVAL.hp_regen_interval)
    assert state.player.hp == 20 - SURVIVAL.hp_regen_interval


def test_max_hp_down_is_restored_on_descend():
    state = new_state(rng_roll=0)
    state._inflict_player("max_hp_down")
    state._inflict_player("max_hp_down")
    assert state.player.max_hp == PARAMS.player.hp - 6
    state.player.x, state.player.y = state.floor.stairs
    state.descend()
    assert state.player.max_hp == PARAMS.player.hp


def test_monster_respawns_every_interval():
    state = new_state(params=PARAMS)
    wait_turns(state, PARAMS.spawn.respawn_interval)
    assert len(state.floor.monsters) == 1
    assert state.fog.state(*state.floor.monsters[0].pos) != Visibility.VISIBLE


def test_new_visible_monster_interrupts_continuous_move():
    state = new_state()
    state.consume_interrupt()
    place_monster(state, "slime", Direction.UP)
    assert state.consume_interrupt()
    state.update_fov()
    assert not state.consume_interrupt()


def test_leaving_room_keeps_it_known():
    state = new_state()
    start_room = state.floor.room_at(*state.player.pos)
    state.player.x, state.player.y = state.floor.stairs
    state.update_fov()
    assert all(state.fog.state(*cell) == Visibility.KNOWN for cell in start_room.cells())


# --- 大きな背負い袋 ---


def test_big_bag_widens_the_inventory_for_this_run():
    state = new_state()
    before = state.inventory.capacity
    bag = ItemInstance(CATALOG.items["big_bag"], count=3)
    state.inventory.add(bag)
    assert state.use_item(bag)
    assert state.inventory.capacity == before + 5
    assert state.use_item(bag)
    assert state.inventory.capacity == before + PARAMS.inventory_bag_bonus_max
    assert not state.use_item(bag)  # 上限に達したら使えず、袋も減らない
    assert bag.count == 1
    assert "これ以上は袋を広げられない" in log_text(state)


def test_items_beyond_the_camp_capacity_are_carried_into_the_next_run():
    state = new_state()
    loadout = Loadout(Inventory(2, PARAMS.inventory_stack_max))
    loadout.items.items = [
        ItemInstance(CATALOG.items["knife"]) for _ in range(4)
    ]  # 袋で広げて持ち帰った
    state.take_loadout(loadout)
    assert len(state.inventory.items) == 4
