"""8方向の定義。仕様書 5.2。

pyxel を import しないこと。
"""

from __future__ import annotations

from enum import Enum

# スプライトの向き（斜めは左右の絵を使う。仕様書 2.3.1）
FACINGS: tuple[str, ...] = ("up", "down", "left", "right")


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    UP_LEFT = (-1, -1)
    UP_RIGHT = (1, -1)
    DOWN_LEFT = (-1, 1)
    DOWN_RIGHT = (1, 1)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def is_diagonal(self) -> bool:
        return self.dx != 0 and self.dy != 0

    @property
    def sprite_facing(self) -> str:
        if self.dx < 0:
            return "left"
        if self.dx > 0:
            return "right"
        return "up" if self.dy < 0 else "down"

    def rotated(self, steps: int) -> Direction:
        """45度ずつ時計回りに steps 回まわした方向（負の値で反時計回り）。"""
        index = _CLOCKWISE.index(self)
        return _CLOCKWISE[(index + steps) % len(_CLOCKWISE)]

    @classmethod
    def from_delta(cls, dx: int, dy: int) -> Direction:
        return cls((dx, dy))

    @classmethod
    def toward(cls, start: tuple[int, int], goal: tuple[int, int]) -> Direction | None:
        """start から goal へ向かう8方向のうちの1つ。同じマスなら None。"""
        dx = (goal[0] > start[0]) - (goal[0] < start[0])
        dy = (goal[1] > start[1]) - (goal[1] < start[1])
        if dx == 0 and dy == 0:
            return None
        return cls((dx, dy))


_CLOCKWISE: tuple[Direction, ...] = (
    Direction.UP,
    Direction.UP_RIGHT,
    Direction.RIGHT,
    Direction.DOWN_RIGHT,
    Direction.DOWN,
    Direction.DOWN_LEFT,
    Direction.LEFT,
    Direction.UP_LEFT,
)


def chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    """8方向移動での距離（何歩で届くか）。"""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
