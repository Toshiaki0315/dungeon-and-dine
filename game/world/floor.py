"""1階層分の状態（タイル、部屋、敵、床アイテム、罠）とエリア定義。仕様書 5章。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from game.world.direction import Direction
from game.world.tiles import WALKABLE_TILES, Tile

if TYPE_CHECKING:
    from game.entities.item import FloorItem
    from game.entities.monster import Monster
    from game.systems.traps import Trap


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h

    def intersects(self, other: Rect) -> bool:
        return (
            self.x < other.x + other.w
            and other.x < self.x + self.w
            and self.y < other.y + other.h
            and other.y < self.y + self.h
        )

    def cells(self) -> Iterator[tuple[int, int]]:
        for y in range(self.y, self.y + self.h):
            for x in range(self.x, self.x + self.w):
                yield x, y


@dataclass
class Floor:
    number: int
    width: int
    height: int
    tiles: list[Tile]  # 行優先の1次元配列（index = y * width + x）
    rooms: list[Rect]
    start: tuple[int, int]
    stairs: tuple[int, int]
    monsters: list[Monster] = field(default_factory=list)  # 生成順
    items: list[FloorItem] = field(default_factory=list)
    traps: list[Trap] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.tiles) != self.width * self.height:
            raise ValueError("tiles の要素数が width × height と一致しません")

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile_at(self, x: int, y: int) -> Tile:
        """タイルを返す。マップ外は壁として扱う。"""
        if not self.in_bounds(x, y):
            return Tile.WALL
        return self.tiles[y * self.width + x]

    def is_walkable(self, x: int, y: int) -> bool:
        return self.tile_at(x, y) in WALKABLE_TILES

    def can_move(self, x: int, y: int, direction: Direction) -> bool:
        """地形だけを見て、その方向へ1歩進めるか（敵などは考慮しない）。"""
        nx, ny = x + direction.dx, y + direction.dy
        if not self.is_walkable(nx, ny):
            return False
        if direction.is_diagonal:
            # 角抜け禁止: 移動方向に隣接する2マスのどちらかが壁なら通れない
            return self.is_walkable(nx, y) and self.is_walkable(x, ny)
        return True

    def is_edge_wall(self, x: int, y: int) -> bool:
        """周囲8マスに歩けるマスがある壁か。部屋や通路の輪郭として描く壁だけが True になる。"""
        if self.is_walkable(x, y):
            return False
        return any(
            self.is_walkable(x + dx, y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy
        )

    def room_at(self, x: int, y: int) -> Rect | None:
        return next((room for room in self.rooms if room.contains(x, y)), None)

    def monster_at(self, x: int, y: int) -> Monster | None:
        return next((m for m in self.monsters if m.x == x and m.y == y), None)

    def item_at(self, x: int, y: int) -> FloorItem | None:
        return next((i for i in self.items if i.x == x and i.y == y), None)

    def trap_at(self, x: int, y: int) -> Trap | None:
        return next((t for t in self.traps if t.x == x and t.y == y), None)


@dataclass(frozen=True)
class Area:
    """エリア（苔むす洞窟など）。floors.json の "areas" で定義する。"""

    id: str
    name: str
    first_floor: int
    last_floor: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Area:
        first, last = data["floors"]
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            first_floor=int(first),
            last_floor=int(last),
        )


def area_for_floor(areas: Sequence[Area], floor_number: int) -> Area:
    for area in areas:
        if area.first_floor <= floor_number <= area.last_floor:
            return area
    raise ValueError(f"B{floor_number}F に対応するエリアが floors.json にありません")
