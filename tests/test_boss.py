"""B20F のボス「奈落の大喰らい」のテスト（フェーズ7）。仕様書 5.3 / 8.3。"""

from game.entities import ai
from game.entities.monster import AI_BOSS
from game.systems.game_state import EFFECT_ROAR, GameState
from game.world.direction import Direction
from game.world.tiles import Tile
from tests.test_game_state import CATALOG, PARAMS, log_text, new_state, place_monster, wait_turns

BOSS_ID = "devourer"
BOSS = CATALOG.monsters[BOSS_ID]
ROAR = next(a for a in BOSS.abilities if a.type == "roar")
ENRAGE = next(a for a in BOSS.abilities if a.type == "enrage")
DEVOUR = next(a for a in BOSS.abilities if a.type == "devour")


def boss_floor_state():
    state = GameState(42, PARAMS)
    state.enter_floor(PARAMS.last_floor)
    return state


def act(state, monster, times=1):
    for _ in range(times):
        ai.take_turn(monster, state, PARAMS.ai)


def place_boss(state, distance=1):
    """プレイヤーの隣（または指定の距離）にボスを置き、耐えられるHPにしておく。"""
    state.player.max_hp = state.player.hp = 500
    return place_monster(state, BOSS_ID, Direction.RIGHT, distance=distance)


# --- 固定レイアウト（仕様書 5.3） ---


def test_boss_floor_has_a_fixed_layout_without_stairs():
    state = boss_floor_state()
    assert state.floor.number == PARAMS.last_floor
    assert len(state.floor.rooms) == 2  # 手前の部屋とボスの間
    assert Tile.STAIRS_DOWN not in state.floor.tiles
    assert state.player_on_stairs is False and state.can_descend is False


def test_boss_floor_is_the_same_every_time():
    """ランシードが違っても、ボス階の形は変わらない。"""
    first = boss_floor_state()
    second = GameState(999, PARAMS)
    second.enter_floor(PARAMS.last_floor)
    assert first.floor.tiles == second.floor.tiles
    assert first.floor.start == second.floor.start


def test_boss_floor_has_a_campfire_in_front_and_one_boss():
    state = boss_floor_state()
    entry = state.floor.rooms[0]
    assert state.floor.in_safe_zone(*entry.center)  # 手前の部屋に焚き火
    assert [m.definition.id for m in state.floor.monsters] == [BOSS_ID]
    assert state.floor.chests == [] and state.floor.traps == []


def test_no_extra_monsters_appear_on_the_boss_floor():
    state = boss_floor_state()
    wait_turns(state, PARAMS.spawn.respawn_interval * 2)
    assert len(state.floor.monsters) == 1


# --- 行動パターン（仕様書 8.3） ---


def test_boss_roars_every_few_turns_and_slows_the_player():
    state = new_state()
    boss = place_boss(state)
    act(state, boss, ROAR.interval)
    assert "咆哮" in log_text(state)
    assert ROAR.status in state.player.statuses
    assert EFFECT_ROAR in [e.kind for e in state.consume_events()]


def test_boss_does_not_roar_from_far_away():
    """咆哮の番でも、射程の外なら使わない（追いかけるだけ）。"""
    state = new_state()
    boss = place_boss(state, distance=ROAR.range + 2)
    boss.turns_acted = ROAR.interval - 1  # 次の行動が咆哮の番
    act(state, boss)
    assert "咆哮" not in log_text(state)
    assert ROAR.status not in state.player.statuses


def test_boss_speeds_up_below_half_hp():
    state = new_state()
    boss = place_boss(state)
    assert boss.speed == BOSS.speed
    boss.hp = int(BOSS.hp * ENRAGE.hp_ratio)
    act(state, boss)
    assert boss.speed == ENRAGE.speed


def test_boss_devours_the_player_below_quarter_hp():
    state = new_state()
    boss = place_boss(state)
    boss.hp = int(BOSS.hp * DEVOUR.hp_ratio)
    before_satiety, before_hp = state.player.satiety, boss.hp
    act(state, boss)
    assert state.player.satiety == before_satiety - DEVOUR.value
    assert boss.hp == before_hp + DEVOUR.value  # 奪ったぶん回復する
    assert "喰らいついた" in log_text(state)


def test_devouring_never_takes_more_than_the_player_has():
    state = new_state()
    boss = place_boss(state)
    boss.hp = int(BOSS.hp * DEVOUR.hp_ratio)
    state.player.satiety = 5
    act(state, boss)
    assert state.player.satiety == 0
    assert boss.hp == int(BOSS.hp * DEVOUR.hp_ratio) + 5


def test_boss_chases_and_attacks_like_a_normal_enemy():
    state = new_state()
    boss = place_boss(state, distance=4)
    act(state, boss)
    assert boss.definition.ai == AI_BOSS
    assert boss.pos != (state.player.x + 4, state.player.y)  # 近づいてくる


def test_defeating_the_boss_clears_the_run():
    state = new_state(rng_roll=0)
    boss = place_boss(state)
    boss.hp = 1
    state.face(Direction.RIGHT)
    state.attack()
    assert state.cleared is True
    assert state.run_over is True
    assert "迷宮の主は崩れ落ちた" in log_text(state)
