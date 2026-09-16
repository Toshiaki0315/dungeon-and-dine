"""タイル種別の定義。仕様書 5.3。

pyxel を import しないこと。
"""

from __future__ import annotations

from enum import IntEnum


class Tile(IntEnum):
    WALL = 0
    FLOOR = 1
    CORRIDOR = 2
    STAIRS_DOWN = 3


WALKABLE_TILES: frozenset[Tile] = frozenset({Tile.FLOOR, Tile.CORRIDOR, Tile.STAIRS_DOWN})

CAMPFIRE_SPRITE = "campfire"  # 焚き火（3コマ）
SAFE_FLOOR_SPRITE = "floor_safe"  # 焚き火の周囲（安全地帯）の床

# sprites.json のキー。エリア別の素材は "<キー>_<エリアID>"（例: wall_moss）で定義できる。
SPRITE_NAMES: dict[Tile, str] = {
    Tile.WALL: "wall",
    Tile.FLOOR: "floor",
    Tile.CORRIDOR: "corridor",
    Tile.STAIRS_DOWN: "stairs_down",
}
