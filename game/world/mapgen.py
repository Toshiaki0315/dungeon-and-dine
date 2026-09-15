"""BSP法によるマップ生成。仕様書 5.3。

pyxel を import しないこと。
"""

from __future__ import annotations

import random
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, fields
from typing import Any

from game.world.floor import Floor, Rect
from game.world.tiles import Tile


class MapGenError(Exception):
    """指定のパラメータでは条件を満たすマップを作れないときに送出する。"""


@dataclass(frozen=True)
class MapGenParams:
    """マップ生成のパラメータ。値は balance.json の "mapgen" で定義する。"""

    width: int
    height: int
    rooms_min: int
    rooms_max: int
    leaf_min_w: int  # BSP で分割した区画の最小サイズ
    leaf_min_h: int
    room_min_w: int
    room_min_h: int
    room_max_w: int
    room_max_h: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MapGenParams:
        missing = [f.name for f in fields(cls) if f.name not in data]
        if missing:
            raise ValueError(f"mapgen: 必須キーがありません: {', '.join(missing)}")
        return cls(**{f.name: int(data[f.name]) for f in fields(cls)})

    def validate(self) -> None:
        if not 2 <= self.rooms_min <= self.rooms_max:
            raise ValueError("rooms_min は2以上かつ rooms_max 以下にしてください")
        if self.room_max_w < self.room_min_w or self.room_max_h < self.room_min_h:
            raise ValueError(
                "room_max_w / room_max_h は room_min_w / room_min_h 以上にしてください"
            )
        # 部屋は区画の内側に1マスの余白を空けて置くため、区画は部屋より2マス以上大きくする
        if self.leaf_min_w < self.room_min_w + 2 or self.leaf_min_h < self.room_min_h + 2:
            raise ValueError("leaf_min_w / leaf_min_h は部屋の最小サイズ + 2 以上にしてください")
        if self.width < self.leaf_min_w + 2 or self.height < self.leaf_min_h + 2:
            raise ValueError("マップが区画の最小サイズより小さくなっています")


@dataclass(eq=False)
class _Node:
    rect: Rect
    left: _Node | None = None
    right: _Node | None = None
    room: Rect | None = None

    def rooms(self) -> list[Rect]:
        if self.left is None or self.right is None:
            return [self.room] if self.room is not None else []
        return self.left.rooms() + self.right.rooms()


def generate_floor(rng: random.Random, number: int, params: MapGenParams) -> Floor:
    """1階層分のマップを生成する。同じ乱数状態・パラメータなら同じマップになる。"""
    params.validate()
    width = params.width
    tiles = [Tile.WALL] * (width * params.height)

    # 外周1マスは必ず壁として残す
    root = _Node(Rect(1, 1, width - 2, params.height - 2))
    leaves = _split(root, rng.randint(params.rooms_min, params.rooms_max), rng, params)
    if len(leaves) < params.rooms_min:
        raise MapGenError(f"部屋を {params.rooms_min} 個置けません（マップが小さすぎます）")

    for leaf in leaves:
        leaf.room = _place_room(leaf.rect, rng, params)
        for x, y in leaf.room.cells():
            tiles[y * width + x] = Tile.FLOOR

    # BSP の兄弟どうしを必ずつなぐので、すべての部屋が到達可能になる
    _connect(root, rng, tiles, width)

    rooms = root.rooms()
    start_room, stairs_room = rng.sample(rooms, 2)
    start = _random_cell(start_room, rng)
    stairs = _random_cell(stairs_room, rng)
    tiles[stairs[1] * width + stairs[0]] = Tile.STAIRS_DOWN

    return Floor(
        number=number,
        width=width,
        height=params.height,
        tiles=tiles,
        rooms=rooms,
        start=start,
        stairs=stairs,
    )


def _split(root: _Node, target: int, rng: random.Random, params: MapGenParams) -> list[_Node]:
    leaves = [root]
    while len(leaves) < target:
        candidates = [node for node in leaves if _can_split(node.rect, params)]
        if not candidates:
            break
        # 大きい区画を優先して分割し、部屋の大きさの偏りを抑える
        largest = max(node.rect.w * node.rect.h for node in candidates)
        node = rng.choice([n for n in candidates if n.rect.w * n.rect.h * 2 >= largest])
        left, right = _split_node(node, rng, params)
        index = leaves.index(node)
        leaves[index : index + 1] = [left, right]
    return leaves


def _can_split(rect: Rect, params: MapGenParams) -> bool:
    return rect.w >= 2 * params.leaf_min_w or rect.h >= 2 * params.leaf_min_h


def _split_node(node: _Node, rng: random.Random, params: MapGenParams) -> tuple[_Node, _Node]:
    r = node.rect
    can_vertical = r.w >= 2 * params.leaf_min_w
    can_horizontal = r.h >= 2 * params.leaf_min_h
    # 両方向に切れるときは、横長の区画ほど縦に切りやすくする
    vertical = rng.random() < r.w / (r.w + r.h) if can_vertical and can_horizontal else can_vertical

    if vertical:
        cut = rng.randint(params.leaf_min_w, r.w - params.leaf_min_w)
        node.left = _Node(Rect(r.x, r.y, cut, r.h))
        node.right = _Node(Rect(r.x + cut, r.y, r.w - cut, r.h))
    else:
        cut = rng.randint(params.leaf_min_h, r.h - params.leaf_min_h)
        node.left = _Node(Rect(r.x, r.y, r.w, cut))
        node.right = _Node(Rect(r.x, r.y + cut, r.w, r.h - cut))
    return node.left, node.right


def _place_room(leaf: Rect, rng: random.Random, params: MapGenParams) -> Rect:
    w = rng.randint(params.room_min_w, min(params.room_max_w, leaf.w - 2))
    h = rng.randint(params.room_min_h, min(params.room_max_h, leaf.h - 2))
    x = rng.randint(leaf.x + 1, leaf.x + leaf.w - 1 - w)
    y = rng.randint(leaf.y + 1, leaf.y + leaf.h - 1 - h)
    return Rect(x, y, w, h)


def _connect(node: _Node, rng: random.Random, tiles: list[Tile], width: int) -> None:
    if node.left is None or node.right is None:
        return
    _connect(node.left, rng, tiles, width)
    _connect(node.right, rng, tiles, width)

    # 左右の部分木から、中心どうしが最も近い部屋の組を通路でつなぐ
    a, b = min(
        ((a, b) for a in node.left.rooms() for b in node.right.rooms()),
        key=lambda pair: _manhattan(pair[0].center, pair[1].center),
    )
    _carve_corridor(tiles, width, a.center, b.center, horizontal_first=rng.random() < 0.5)


def _carve_corridor(
    tiles: list[Tile],
    width: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    *,
    horizontal_first: bool,
) -> None:
    """L字の通路を掘る。部屋の床は上書きしない。"""
    corner = (goal[0], start[1]) if horizontal_first else (start[0], goal[1])
    for a, b in ((start, corner), (corner, goal)):
        for x, y in _segment(a, b):
            index = y * width + x
            if tiles[index] == Tile.WALL:
                tiles[index] = Tile.CORRIDOR


def _segment(a: tuple[int, int], b: tuple[int, int]) -> Iterator[tuple[int, int]]:
    """縦または横の線分上のマスを両端を含めて返す。"""
    (ax, ay), (bx, by) = a, b
    step_x = (bx > ax) - (bx < ax)
    step_y = (by > ay) - (by < ay)
    x, y = ax, ay
    yield x, y
    while (x, y) != (bx, by):
        x += step_x
        y += step_y
        yield x, y


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _random_cell(rect: Rect, rng: random.Random) -> tuple[int, int]:
    return (rng.randint(rect.x, rect.x + rect.w - 1), rng.randint(rect.y, rect.y + rect.h - 1))
