from dataclasses import dataclass

from game.systems.turn import ACTION_COST, TurnScheduler


@dataclass
class Dummy:
    name: str
    speed: int = 100
    energy: int = ACTION_COST


def run_actions(scheduler, player, monsters, count):
    acted = []
    turns = []
    for _ in range(count):
        scheduler.after_player_action(
            player, monsters, act=lambda m: acted.append(m.name), end_turn=turns.append
        )
    return acted, turns


def test_normal_speed_player_advances_one_turn_per_action():
    scheduler = TurnScheduler()
    player = Dummy("player")
    _, turns = run_actions(scheduler, player, [], 3)
    assert scheduler.turn == 3
    assert turns == [1, 2, 3]
    assert player.energy == ACTION_COST


def test_monsters_act_in_creation_order_after_player():
    scheduler = TurnScheduler()
    monsters = [Dummy("rat"), Dummy("slime")]
    acted, _ = run_actions(scheduler, Dummy("player"), monsters, 2)
    assert acted == ["rat", "slime", "rat", "slime"]


def test_slow_player_lets_time_pass_twice():
    scheduler = TurnScheduler()
    player = Dummy("player", speed=50)
    monster = Dummy("rat")
    acted, _ = run_actions(scheduler, player, [monster], 1)
    assert scheduler.turn == 2
    assert acted == ["rat", "rat"]


def test_hasted_player_acts_twice_per_turn():
    scheduler = TurnScheduler()
    player = Dummy("player", speed=200)
    run_actions(scheduler, player, [], 4)
    assert scheduler.turn == 2


def test_fast_monster_acts_twice_per_turn():
    scheduler = TurnScheduler()
    bat = Dummy("bat", speed=200)
    acted, _ = run_actions(scheduler, Dummy("player"), [bat], 3)
    # 1回目は初期エネルギーぶんの1回、以降は毎ターン2回
    assert acted.count("bat") == 5


def test_stop_ends_time_progress_immediately():
    scheduler = TurnScheduler()
    player = Dummy("player", speed=50)
    scheduler.after_player_action(
        player, [], act=lambda m: None, end_turn=lambda t: None, stop=lambda: True
    )
    assert scheduler.turn == 1
