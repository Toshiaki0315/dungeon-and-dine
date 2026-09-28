"""入力の解釈のテスト（仕様書 3.2）。pyxel のキー判定を差し替えて確かめる。"""

import pytest
import pyxel

from game.ui.input import Controls, MoveCommand, TurnCommand
from game.world.direction import Direction


class Keys:
    """いま押しているキー。`just` は押した瞬間のキー。"""

    def __init__(self) -> None:
        self.held: set[int] = set()
        self.just: set[int] = set()

    def press(self, *keys: int) -> None:
        self.just = {k for k in keys if k not in self.held}
        self.held |= set(keys)

    def hold(self, *keys: int) -> None:
        """押したままにする（押した瞬間ではない）。"""
        self.just = set()
        self.held = set(keys)


@pytest.fixture
def keys(monkeypatch):
    state = Keys()
    monkeypatch.setattr(pyxel, "btn", lambda key: key in state.held)
    monkeypatch.setattr(pyxel, "btnp", lambda key, hold=None, repeat=None: key in state.just)
    return state


def controls() -> Controls:
    return Controls(0.15)


def test_single_arrow_moves_straight(keys):
    c = controls()
    keys.press(pyxel.KEY_RIGHT)
    assert c.direction_command() == MoveCommand(Direction.RIGHT)


def test_two_arrows_move_diagonally_without_shift(keys):
    c = controls()
    keys.press(pyxel.KEY_UP)
    c.direction_command()
    keys.press(pyxel.KEY_RIGHT)
    assert c.direction_command() == MoveCommand(Direction.UP_RIGHT)


def test_numpad_diagonal_still_works(keys):
    c = controls()
    keys.press(pyxel.KEY_KP_1)
    assert c.direction_command() == MoveCommand(Direction.DOWN_LEFT)


def test_shift_keeps_accepting_only_diagonals(keys):
    c = controls()
    keys.press(pyxel.KEY_SHIFT, pyxel.KEY_RIGHT)
    assert c.direction_command() is None  # 斜めになっていないので動かない
    keys.press(pyxel.KEY_UP)
    assert c.direction_command() == MoveCommand(Direction.UP_RIGHT)


def test_turn_modifier_turns_without_moving(keys):
    c = controls()
    keys.press(pyxel.KEY_CTRL, pyxel.KEY_UP)
    c.direction_command()
    keys.press(pyxel.KEY_LEFT)
    assert c.direction_command() == TurnCommand(Direction.UP_LEFT)


def test_releasing_one_arrow_goes_back_to_straight(keys):
    c = controls()
    keys.press(pyxel.KEY_UP)
    c.direction_command()
    keys.press(pyxel.KEY_RIGHT)
    c.direction_command()
    keys.hold(pyxel.KEY_RIGHT)
    assert c.direction_command() == MoveCommand(Direction.RIGHT)
