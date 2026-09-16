"""演出イベント（効果音・ダメージ表示のもとになる出来事）のテスト（フェーズ7）。仕様書 14章。"""

from game.entities.monster import MODE_CHASE
from game.systems.game_state import (
    EFFECT_ATTACK,
    EFFECT_DEATH,
    EFFECT_HIT,
    EFFECT_LEVEL_UP,
    EFFECT_PICKUP,
    EFFECT_STAIRS,
)
from game.world.direction import Direction
from tests.test_game_state import new_state, place_item, place_monster


def kinds(state):
    return [event.kind for event in state.consume_events()]


def test_attacking_emits_attack_and_damage_events():
    state = new_state(rng_roll=0)
    monster = place_monster(state, "slime")
    state.face(Direction.RIGHT)
    state.attack()

    events = state.consume_events()
    assert [e.kind for e in events][0] == EFFECT_ATTACK
    hit = next(e for e in events if e.kind == EFFECT_HIT)
    assert (hit.x, hit.y) == monster.pos  # ダメージ表示は敵の位置に出す
    assert hit.value > 0 and hit.on_player is False


def test_taking_damage_is_marked_as_the_players():
    state = new_state(rng_roll=0)
    place_monster(state, "giant_rat", mode=MODE_CHASE)
    state.wait()  # 敵が攻撃してくる
    hits = [e for e in state.consume_events() if e.kind == EFFECT_HIT and e.on_player]
    assert hits and (hits[0].x, hits[0].y) == state.player.pos


def test_level_up_emits_an_event_at_the_player():
    state = new_state(rng_roll=0)
    place_monster(state, "skeleton", hp=1)  # 経験値20でレベルが上がる
    state.face(Direction.RIGHT)
    state.attack()
    events = state.consume_events()
    level_up = next(e for e in events if e.kind == EFFECT_LEVEL_UP)
    assert (level_up.x, level_up.y) == state.player.pos
    assert state.player.level == 2


def test_picking_up_and_descending_emit_events():
    state = new_state()
    place_item(state, "herb", Direction.RIGHT)
    state.move_player(Direction.RIGHT)
    assert EFFECT_PICKUP in kinds(state)

    state.player.x, state.player.y = state.floor.stairs
    state.descend()
    assert EFFECT_STAIRS in kinds(state)


def test_death_emits_an_event_once():
    state = new_state()
    state.player.hp = 1
    state.player.satiety = 0
    state.wait()  # 飢餓で力尽きる
    assert state.is_game_over
    assert kinds(state).count(EFFECT_DEATH) == 1
