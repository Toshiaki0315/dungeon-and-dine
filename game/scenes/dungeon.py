"""ダンジョン探索シーン。仕様書 4章。

フェーズ1では、マップ生成・移動・カメラのスクロールまでを扱う。
"""

from __future__ import annotations

from typing import Any

import pyxel

from game import config, rng
from game.entities.player import Player
from game.scenes import Scene
from game.ui import font
from game.ui.camera import camera_origin
from game.ui.input import Controls, MoveCommand, TurnCommand
from game.ui.sprites import SpriteSheet
from game.world.floor import Area, Floor, area_for_floor
from game.world.mapgen import MapGenParams, generate_floor
from game.world.tiles import SPRITE_NAMES, Tile

FLOOR_BANNER_SECONDS = 2

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_FRAME = 1
COLOR_DEBUG = 10


class DungeonScene:
    def __init__(
        self,
        *,
        run_seed: int,
        data: dict[str, dict[str, Any]],
        sprites: SpriteSheet,
        controls: Controls,
        debug: bool,
    ) -> None:
        self.run_seed = run_seed
        self.sprites = sprites
        self.controls = controls
        self.debug = debug
        self.show_debug = False

        self.areas = [Area.from_dict(a) for a in data["floors"]["areas"]]
        self.mapgen_params = MapGenParams.from_dict(data["balance"]["mapgen"])

        self.player = Player(0, 0)
        self.floor: Floor
        self.area: Area
        self.banner_frames = 0
        self.enter_floor(1)

    def enter_floor(self, number: int) -> None:
        self.floor = generate_floor(
            rng.floor_rng(self.run_seed, number), number, self.mapgen_params
        )
        self.area = area_for_floor(self.areas, number)
        self.player.x, self.player.y = self.floor.start
        self.banner_frames = FLOOR_BANNER_SECONDS * config.FPS

    # --- update ---

    def update(self) -> Scene | None:
        if self.debug and self.controls.triggered("debug"):
            self.show_debug = not self.show_debug

        command = self.controls.direction_command()
        if isinstance(command, MoveCommand):
            self.player.try_move(self.floor, command.direction)
        elif isinstance(command, TurnCommand):
            self.player.facing = command.direction

        if self.banner_frames > 0:
            self.banner_frames -= 1
        return None

    # --- draw ---

    def draw(self) -> None:
        pyxel.cls(0)
        self._draw_map()
        self._draw_status_bar()
        self._draw_bottom_panel()
        if self.banner_frames > 0:
            self._draw_floor_banner()

    def _floor_label(self) -> str:
        return f"B{self.floor.number}F {self.area.name}"

    def _draw_map(self) -> None:
        ts = config.TILE_SIZE
        view_w, view_h = config.MAP_VIEW_TILES_W, config.MAP_VIEW_TILES_H
        cam_x, cam_y = camera_origin(
            self.player.x, self.player.y, self.floor.width, self.floor.height, view_w, view_h
        )
        frame = pyxel.frame_count // config.ANIMATION_TICKS

        pyxel.clip(0, config.MAP_TOP, config.SCREEN_WIDTH, config.MAP_VIEW_HEIGHT)
        for ty in range(view_h):
            for tx in range(view_w):
                mx, my = cam_x + tx, cam_y + ty
                tile = self.floor.tile_at(mx, my)
                # 部屋や通路に接していない岩盤は描かず、黒のままにする
                if tile == Tile.WALL and not self.floor.is_edge_wall(mx, my):
                    continue
                name = self._tile_sprite(tile)
                self.sprites.draw(name, tx * ts, config.MAP_TOP + ty * ts, frame, colkey=None)

        self.sprites.draw(
            self.player.sprite_name,
            (self.player.x - cam_x) * ts,
            config.MAP_TOP + (self.player.y - cam_y) * ts,
            frame,
        )
        pyxel.clip()

    def _tile_sprite(self, tile: Tile) -> str:
        """エリア別の素材（例: wall_moss）があればそれを、なければ共通の素材を使う。"""
        base = SPRITE_NAMES[tile]
        area_specific = f"{base}_{self.area.id}"
        return area_specific if self.sprites.has(area_specific) else base

    def _draw_status_bar(self) -> None:
        # フェーズ2で Lv・EXP・ゲージを含むステータスバー（ui/hud.py）に置き換える
        font.draw_text(2, 1, self._floor_label(), COLOR_TEXT)
        pyxel.line(0, config.MAP_TOP - 1, config.SCREEN_WIDTH - 1, config.MAP_TOP - 1, COLOR_FRAME)

    def _draw_bottom_panel(self) -> None:
        # フェーズ2でコマンドバーとログ（ui/command_bar.py, ui/log.py）に置き換える
        top = config.MAP_TOP + config.MAP_VIEW_HEIGHT
        pyxel.line(0, top, config.SCREEN_WIDTH - 1, top, COLOR_FRAME)
        font.draw_text(2, top + 3, "移動: 矢印/WASD  斜め: Shift+2方向/テンキー", COLOR_SUBTEXT)
        font.draw_text(2, top + 3 + config.LINE_HEIGHT, "向きだけ変える: Ctrl+方向", COLOR_SUBTEXT)
        if self.show_debug:
            font.draw_text(
                2,
                top + 3 + config.LINE_HEIGHT * 2,
                f"SEED {self.run_seed}  POS {self.player.x},{self.player.y}",
                COLOR_DEBUG,
            )

    def _draw_floor_banner(self) -> None:
        label = self._floor_label()
        width = font.text_width(label)
        x = (config.SCREEN_WIDTH - width) // 2
        y = config.MAP_TOP + (config.MAP_VIEW_HEIGHT - config.TILE_SIZE) // 2
        pyxel.rect(x - 6, y - 4, width + 12, 16, 0)
        pyxel.rectb(x - 6, y - 4, width + 12, 16, COLOR_SUBTEXT)
        font.draw_text(x, y, label, COLOR_TEXT)
