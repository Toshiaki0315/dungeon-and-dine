"""全体マップ（地図コマンド）。仕様書 14章。"""

from __future__ import annotations

import pyxel

from game import config
from game.ui import font
from game.world.floor import Floor
from game.world.fov import FogMap, Visibility
from game.world.tiles import Tile

CELL_W = 4  # 1タイル = 4×2 px
CELL_H = 2

COLOR_TEXT = 7
COLOR_HINT = 13
COLOR_WALKABLE = 5
COLOR_WALL = 1
COLOR_STAIRS = 10
COLOR_PLAYER = 8
BLINK_TICKS = 8


def draw_full_map(floor: Floor, fog: FogMap, player_pos: tuple[int, int], title: str) -> None:
    """既知のタイル・階段・プレイヤーの位置だけを縮小して描く。"""
    font.draw_text(4, 3, f"地図  {title}", COLOR_TEXT)
    map_w, map_h = floor.width * CELL_W, floor.height * CELL_H
    ox = (config.SCREEN_WIDTH - map_w) // 2
    oy = (config.SCREEN_HEIGHT - map_h) // 2

    for y in range(floor.height):
        for x in range(floor.width):
            if fog.state(x, y) == Visibility.UNEXPLORED:
                continue
            color = _tile_color(floor, x, y)
            if color is not None:
                pyxel.rect(ox + x * CELL_W, oy + y * CELL_H, CELL_W, CELL_H, color)

    if (pyxel.frame_count // BLINK_TICKS) % 2 == 0:
        px, py = player_pos
        pyxel.rect(ox + px * CELL_W, oy + py * CELL_H, CELL_W, CELL_H, COLOR_PLAYER)

    font.draw_text(4, config.SCREEN_HEIGHT - 11, "M / Esc: 閉じる", COLOR_HINT)


def _tile_color(floor: Floor, x: int, y: int) -> int | None:
    tile = floor.tile_at(x, y)
    if tile == Tile.STAIRS_DOWN:
        return COLOR_STAIRS
    if floor.is_walkable(x, y):
        return COLOR_WALKABLE
    if floor.is_edge_wall(x, y):
        return COLOR_WALL
    return None
