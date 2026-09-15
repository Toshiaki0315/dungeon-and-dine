from game import data_loader
from game.systems.game_state import GameParams, GameState
from game.world.direction import Direction
from game.world.fov import Visibility

PARAMS = GameParams.from_data(data_loader.load_all())
SURVIVAL = PARAMS.survival


def new_state(seed=42):
    return GameState(seed, PARAMS)


def open_direction(state):
    return next(d for d in Direction if state.floor.can_move(*state.player.pos, d))


def wait_turns(state, count):
    for _ in range(count):
        state.wait()


def test_new_run_starts_on_b1f_with_initial_stats():
    state = new_state()
    assert state.floor.number == 1
    assert state.area.name == "苔むす洞窟"
    assert state.turn == 0
    assert state.player.pos == state.floor.start
    assert state.player.hp == state.player.max_hp == PARAMS.player.hp
    assert state.player.satiety == PARAMS.player.satiety
    assert state.log.entries


def test_move_consumes_one_turn():
    state = new_state()
    assert state.move_player(open_direction(state))
    assert state.turn == 1


def test_blocked_move_and_facing_do_not_consume_turn():
    state = new_state()
    room = state.floor.room_at(*state.player.pos)
    state.player.x, state.player.y = room.x, room.y  # 部屋の左上の角
    assert not state.move_player(Direction.UP_LEFT)
    state.face(Direction.RIGHT)
    assert state.turn == 0
    assert state.player.facing == Direction.RIGHT


def test_satiety_decreases_as_turns_pass():
    state = new_state()
    interval = SURVIVAL.satiety_decay_interval
    wait_turns(state, interval - 1)
    assert state.player.satiety == PARAMS.player.satiety
    wait_turns(state, 1)
    assert state.player.satiety == PARAMS.player.satiety - 1
    wait_turns(state, interval * 9)
    assert state.player.satiety == PARAMS.player.satiety - 10


def test_hunger_messages_are_logged():
    state = new_state()
    state.player.satiety = SURVIVAL.hunger_warning_threshold + 1
    wait_turns(state, SURVIVAL.satiety_decay_interval)
    assert any("おなかが減ってきた" in e for e in state.log.entries)


def test_starvation_leads_to_game_over():
    state = new_state()
    state.player.satiety = 0
    state.player.hp = 2
    state.wait()
    assert not state.is_game_over
    state.wait()
    assert state.is_game_over
    assert "力尽きた" in state.log.latest(1)[0]

    turn = state.turn
    state.wait()
    assert not state.move_player(open_direction(state))
    assert state.turn == turn


def test_descend_requires_standing_on_stairs():
    state = new_state()
    assert not state.player_on_stairs
    assert not state.descend()
    assert state.floor.number == 1


def test_descend_generates_next_floor_and_resets_fog():
    state = new_state()
    old_tiles = state.floor.tiles
    state.player.x, state.player.y = state.floor.stairs
    state.player.mp = 0
    turn = state.turn

    assert state.descend()
    assert state.floor.number == 2
    assert state.floor.tiles != old_tiles
    assert state.player.pos == state.floor.start
    assert state.turn == turn
    assert state.player.mp == int(PARAMS.player.mp * SURVIVAL.descend_mp_recover_ratio)
    # 新しい階の探索状況に切り替わり、今見えているマスだけが探索済みになっている
    visible_count = sum(
        state.fog.state(x, y) == Visibility.VISIBLE
        for y in range(state.floor.height)
        for x in range(state.floor.width)
    )
    assert state.fog.explored_count == visible_count
    room = state.floor.room_at(*state.player.pos)
    assert all(state.fog.state(*cell) == Visibility.VISIBLE for cell in room.cells())


def test_cannot_descend_from_last_floor():
    state = new_state()
    state.enter_floor(PARAMS.last_floor)
    state.player.x, state.player.y = state.floor.stairs
    assert state.player_on_stairs
    assert not state.can_descend
    assert not state.descend()


def test_leaving_room_keeps_it_known():
    state = new_state()
    start_room = state.floor.room_at(*state.player.pos)
    # 階段のある別の部屋へ移動すると、最初の部屋は既知（視界外）になる
    state.player.x, state.player.y = state.floor.stairs
    state.update_fov()
    assert all(state.fog.state(*cell) == Visibility.KNOWN for cell in start_room.cells())
