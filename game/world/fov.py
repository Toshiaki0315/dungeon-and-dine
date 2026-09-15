"""視界（未踏／既知／視界内）の計算。仕様書 5.4。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from game.data_loader import dataclass_from_dict
from game.world.direction import Direction
from game.world.floor import Floor, Rect


class Visibility(IntEnum):
    UNEXPLORED = 0
    KNOWN = 1
    VISIBLE = 2


@dataclass(frozen=True)
class FovParams:
    """視界のパラメータ。balance.json の "fov" で定義する。"""

    corridor_adjacent: int  # 通路で見える周囲の範囲（兜の視界拡張で +1）
    corridor_forward: int  # 通路で進行方向に見える直線の距離

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FovParams:
        return dataclass_from_dict(cls, data, "fov")


def compute_visible(
    floor: Floor,
    x: int,
    y: int,
    facing: Direction,
    params: FovParams,
    *,
    blind: bool = False,
) -> set[tuple[int, int]]:
    """(x, y) にいて facing を向いているときに見えるマスを返す。"""
    radius = 1 if blind else params.corridor_adjacent
    visible = _square(floor, x, y, radius)
    if blind:
        return visible

    room = floor.room_at(x, y)
    if room is not None:
        # 部屋の中は、壁を含めて部屋全体が見える
        walls = Rect(room.x - 1, room.y - 1, room.w + 2, room.h + 2)
        visible.update(cell for cell in walls.cells() if floor.in_bounds(*cell))
        return visible

    # 通路では、進行方向に直線で最大 corridor_forward マス見える（壁で遮られる）
    cx, cy = x, y
    for _ in range(params.corridor_forward):
        cx, cy = cx + facing.dx, cy + facing.dy
        if not floor.in_bounds(cx, cy):
            break
        visible.add((cx, cy))
        if not floor.is_walkable(cx, cy):
            break
    return visible


def _square(floor: Floor, x: int, y: int, radius: int) -> set[tuple[int, int]]:
    return {
        (x + dx, y + dy)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if floor.in_bounds(x + dx, y + dy)
    }


class FogMap:
    """1階層分の探索状況。"""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._explored = [False] * (width * height)
        self._visible: set[tuple[int, int]] = set()

    def update(self, visible: Iterable[tuple[int, int]]) -> None:
        """現在の視界を差し替え、見えたマスを探索済みにする。"""
        self._visible = {(x, y) for x, y in visible if 0 <= x < self.width and 0 <= y < self.height}
        for x, y in self._visible:
            self._explored[y * self.width + x] = True

    def state(self, x: int, y: int) -> Visibility:
        if (x, y) in self._visible:
            return Visibility.VISIBLE
        if 0 <= x < self.width and 0 <= y < self.height and self._explored[y * self.width + x]:
            return Visibility.KNOWN
        return Visibility.UNEXPLORED

    @property
    def explored_count(self) -> int:
        return sum(self._explored)
