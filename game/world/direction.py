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

    @classmethod
    def from_delta(cls, dx: int, dy: int) -> Direction:
        return cls((dx, dy))
