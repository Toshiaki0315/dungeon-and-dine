"""1階層分の状態（タイル、部屋、敵、床アイテム、宝箱、罠、焚き火）とエリア定義。仕様書 5章。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from game.world.direction import Direction, chebyshev
from game.world.tiles import WALKABLE_TILES, Tile

if TYPE_CHECKING:
    from game.entities.item import Chest, FloorItem
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


SAFE_ZONE_RADIUS = 1  # 焚き火の周囲8マスは安全地帯（仕様書 9.3）


@dataclass(eq=False)
class Campfire:
    """焚き火。隣接するか上に立つと料理できる。周囲は敵が入れない安全地帯になる。"""

    x: int
    y: int
    expires_at: int | None = None  # このターンの終わりに消える（「火起こし」）。None は消えない

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass(eq=False)
class Merchant:
    """迷宮の行商人。隣接するか上に立つと話しかけられる（仕様書 12.4）。

    道具の売買・解呪・解毒をまとめて引き受ける。焚き火と同じく、周囲は敵が入れない。
    """

    x: int
    y: int

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)


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
    chests: list[Chest] = field(default_factory=list)
    traps: list[Trap] = field(default_factory=list)
    campfires: list[Campfire] = field(default_factory=list)
    merchants: list[Merchant] = field(default_factory=list)
    kindled: bool = False  # この階で「火起こし」を使ったか

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
        """地形だけを見て、その方向へ1歩進めるか（敵や宝箱は考慮しない）。"""
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

    def chest_at(self, x: int, y: int) -> Chest | None:
        return next((c for c in self.chests if c.x == x and c.y == y), None)

    def trap_at(self, x: int, y: int) -> Trap | None:
        return next((t for t in self.traps if t.x == x and t.y == y), None)

    def campfire_at(self, x: int, y: int) -> Campfire | None:
        return next((c for c in self.campfires if c.x == x and c.y == y), None)

    def merchant_at(self, x: int, y: int) -> Merchant | None:
        return next((m for m in self.merchants if m.x == x and m.y == y), None)

    def merchant_near(self, x: int, y: int) -> Merchant | None:
        """その場所か隣の8マスにいる行商人（話しかけられる範囲。仕様書 12.4）。"""
        return next((m for m in self.merchants if chebyshev((x, y), m.pos) <= 1), None)

    def in_safe_zone(self, x: int, y: int) -> bool:
        """焚き火のマスか、その周囲8マスか。料理できる範囲とも同じ。"""
        return any(chebyshev((x, y), c.pos) <= SAFE_ZONE_RADIUS for c in self.campfires)


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


def cycle_length(areas: Sequence[Area]) -> int:
    """エリア定義が覆う階数。これを1周とし、それより下は同じ並びをくり返す。"""
    return max(area.last_floor for area in areas)


def cycle_for_floor(areas: Sequence[Area], floor_number: int) -> int:
    """その階が何周目か。1周目（B1F〜B20F）は0を返す。"""
    if floor_number < 1:
        return 0
    return (floor_number - 1) // cycle_length(areas)


def template_floor(areas: Sequence[Area], floor_number: int) -> int:
    """その階が、1周目のどの階にあたるか（B21F なら B1F、B40F なら B20F）。"""
    if floor_number < 1:
        return floor_number
    return (floor_number - 1) % cycle_length(areas) + 1


def area_for_floor(areas: Sequence[Area], floor_number: int) -> Area:
    """その階のエリア。1周分の定義を、深いほうへくり返して使う。"""
    template = template_floor(areas, floor_number)
    for area in areas:
        if area.first_floor <= template <= area.last_floor:
            return area
    raise ValueError(f"B{floor_number}F に対応するエリアが floors.json にありません")


def area_label(areas: Sequence[Area], floor_number: int) -> str:
    """画面に出すエリア名。2周目より下は「（深層2）」のように付ける。"""
    area = area_for_floor(areas, floor_number)
    cycle = cycle_for_floor(areas, floor_number)
    return area.name if cycle == 0 else f"{area.name}（深層{cycle + 1}）"
