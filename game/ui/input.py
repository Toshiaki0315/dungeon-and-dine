"""入力の解釈（キーボード・ゲームパッド）。仕様書 3.2。"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pyxel

from game import config
from game.world.direction import Direction


@dataclass(frozen=True)
class MoveCommand:
    direction: Direction


@dataclass(frozen=True)
class TurnCommand:
    direction: Direction


_ORTHOGONAL_ACTIONS: dict[str, Direction] = {
    "up": Direction.UP,
    "down": Direction.DOWN,
    "left": Direction.LEFT,
    "right": Direction.RIGHT,
}
_DIAGONAL_ACTIONS: dict[str, Direction] = {
    "up_left": Direction.UP_LEFT,
    "up_right": Direction.UP_RIGHT,
    "down_left": Direction.DOWN_LEFT,
    "down_right": Direction.DOWN_RIGHT,
}
_DIRECTION_ACTIONS: dict[str, Direction] = _ORTHOGONAL_ACTIONS | _DIAGONAL_ACTIONS


class Controls:
    """config.KEY_BINDINGS に従って入力を判定する。update 中に毎フレーム1回だけ呼ぶこと。"""

    def __init__(self, repeat_interval_sec: float, fps: int = config.FPS) -> None:
        self._repeat_frames = max(1, math.ceil(repeat_interval_sec * fps))
        self._bindings: dict[str, tuple[int, ...]] = {
            action: tuple(getattr(pyxel, name) for name in names)
            for action, names in config.KEY_BINDINGS.items()
        }
        self._press_order: list[str] = []  # 押された順（最後が最新）
        self._held_direction: Direction | None = None
        self._held_frames = 0
        self._suppressed: Direction | None = None  # 中断中の方向（離すか変えるまで無効）

    def pressed(self, action: str) -> bool:
        return any(pyxel.btn(key) for key in self._bindings[action])

    def triggered(self, action: str) -> bool:
        return any(pyxel.btnp(key) for key in self._bindings[action])

    def triggered_repeat(self, action: str) -> bool:
        """押した瞬間と、押しっぱなしの間の一定間隔で True（メニューのカーソル移動用）。"""
        frames = self._repeat_frames
        return any(pyxel.btnp(key, hold=frames, repeat=frames) for key in self._bindings[action])

    def clicked(self) -> tuple[int, int] | None:
        """左クリックした瞬間の画面座標（決定に対応する）。"""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return (pyxel.mouse_x, pyxel.mouse_y)
        return None

    def right_clicked(self) -> bool:
        """右クリックした瞬間（キャンセルに対応する）。"""
        return pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT)

    def wheel(self) -> int:
        """ホイールの回転量（手前に回すと負。一覧のスクロールに使う）。"""
        return pyxel.mouse_wheel

    def direction_command(self) -> MoveCommand | TurnCommand | None:
        """方向入力を移動（または Ctrl / RB で向きだけ変える）コマンドに変換する。

        押した瞬間に1回、押しっぱなしなら repeat_interval_sec ごとに1回発行する。
        """
        direction = self._current_direction()
        if direction != self._suppressed:
            self._suppressed = None
        if direction != self._held_direction:
            self._held_direction = direction
            self._held_frames = 0
        else:
            self._held_frames += 1

        if direction is None or self._suppressed is not None:
            return None
        if self._held_frames % self._repeat_frames != 0:
            return None
        if self.pressed("turn_modifier"):
            return TurnCommand(direction)
        return MoveCommand(direction)

    def interrupt_repeat(self) -> None:
        """押しっぱなしの連続移動を止める。キーを離すか、別の方向を押すまで再開しない。"""
        self._suppressed = self._held_direction

    def _current_direction(self) -> Direction | None:
        for action in _DIRECTION_ACTIONS:
            if self.triggered(action):
                if action in self._press_order:
                    self._press_order.remove(action)
                self._press_order.append(action)
        self._press_order = [a for a in self._press_order if self.pressed(a)]
        if not self._press_order:
            return None

        # テンキーの斜めと、縦横2方向の同時押しは斜めとして扱う（Shift を押さなくてもよい）
        latest_diagonal = self._latest(_DIAGONAL_ACTIONS)
        if latest_diagonal is not None:
            return latest_diagonal
        vertical = self._latest({"up": Direction.UP, "down": Direction.DOWN})
        horizontal = self._latest({"left": Direction.LEFT, "right": Direction.RIGHT})
        if vertical is not None and horizontal is not None:
            return Direction.from_delta(horizontal.dx, vertical.dy)
        if self.pressed("diagonal_modifier"):
            return None  # Shift / LB を押している間は、斜めだけを受け付ける
        return _DIRECTION_ACTIONS[self._press_order[-1]]

    def _latest(self, actions: dict[str, Direction]) -> Direction | None:
        for action in reversed(self._press_order):
            if action in actions:
                return actions[action]
        return None
