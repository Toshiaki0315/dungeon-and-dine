"""ダンジョン探索シーン。仕様書 4章。

ゲームの状態とターン進行は systems/game_state.py が持ち、このシーンは入力と描画を担当する。
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto

import pyxel

from game import config
from game.scenes import Scene
from game.scenes.game_over import GameOverScene
from game.systems.game_state import GameState
from game.systems.progression import exp_to_next_level
from game.ui import font, hud, minimap
from game.ui.camera import camera_origin
from game.ui.command_bar import COMMANDS, CommandBar, command_label, hit_test
from game.ui.input import Controls, MoveCommand, TurnCommand
from game.ui.inventory_view import draw_inventory
from game.ui.log import LogHistoryView, draw_recent
from game.ui.menu import ConfirmDialog
from game.ui.sprites import SpriteSheet
from game.world.fov import Visibility
from game.world.tiles import SPRITE_NAMES, Tile

FLOOR_BANNER_SECONDS = 2

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_FRAME = 1
COLOR_DEBUG = 10

# 既知タイル（視界外）を暗く描くためのパレット置き換え（仕様書 2.3.1）
KNOWN_TILE_PALETTE: dict[int, int] = {
    1: 0, 2: 1, 3: 1, 4: 2, 5: 1, 6: 5, 7: 13, 8: 2,
    9: 4, 10: 9, 11: 3, 12: 5, 13: 5, 14: 8, 15: 4,
}  # fmt: skip

# ショートカットキー → コマンドID（仕様書 3.2）
SHORTCUTS: dict[str, str] = {
    "inventory": "items",
    "skills": "skills",
    "cook": "cook",
    "equipment": "equipment",
    "map": "map",
}


class Mode(Enum):
    """ダンジョン内のサブモード。EXPLORE 以外を開いている間はターンが進まない。"""

    EXPLORE = auto()
    COMMAND_BAR = auto()
    INVENTORY = auto()
    FULL_MAP = auto()
    CONFIRM = auto()
    LOG_HISTORY = auto()


class DungeonScene:
    def __init__(
        self,
        *,
        state: GameState,
        sprites: SpriteSheet,
        controls: Controls,
        debug: bool,
        new_run: Callable[[], Scene],
    ) -> None:
        self.state = state
        self.sprites = sprites
        self.controls = controls
        self.debug = debug
        self.new_run = new_run
        self.show_debug = False

        self.mode = Mode.EXPLORE
        self.command_bar = CommandBar()
        self.dialog: ConfirmDialog | None = None
        self.log_history = LogHistoryView(state.log)
        self.banner_frames = FLOOR_BANNER_SECONDS * config.FPS

    # --- update ---

    def update(self) -> Scene | None:
        # 押しっぱなしの判定を保つため、方向入力はモードにかかわらず毎フレーム読む
        direction_command = self.controls.direction_command()
        if self.debug and self.controls.triggered("debug"):
            self.show_debug = not self.show_debug
        if self.banner_frames > 0:
            self.banner_frames -= 1

        if self.mode in (Mode.EXPLORE, Mode.COMMAND_BAR) and self._handle_click():
            pass
        elif self.mode == Mode.EXPLORE:
            self._update_explore(direction_command)
        elif self.mode == Mode.COMMAND_BAR:
            self._update_command_bar()
        elif self.mode == Mode.INVENTORY:
            self._close_on("inventory")
        elif self.mode == Mode.FULL_MAP:
            self._close_on("map")
        elif self.mode == Mode.CONFIRM:
            self._update_dialog()
        elif self.mode == Mode.LOG_HISTORY and self.log_history.update(self.controls):
            self.mode = Mode.EXPLORE

        if self.state.is_game_over:
            return GameOverScene(
                player_name=self.state.player.name,
                floor_number=self.state.floor.number,
                turn=self.state.turn,
                controls=self.controls,
                new_run=self.new_run,
            )
        return None

    def _update_explore(self, direction_command: MoveCommand | TurnCommand | None) -> None:
        c = self.controls
        if c.triggered("command_bar"):
            self.mode = Mode.COMMAND_BAR
            return
        for action, command_id in SHORTCUTS.items():
            if c.triggered(action):
                self._execute_command(command_id)
                return
        if c.triggered("log_history"):
            self.log_history.open()
            self.mode = Mode.LOG_HISTORY
            return
        if c.triggered("notebook"):
            self.state.log.add("レシピ手帳は未実装です。")
            return
        if c.triggered("confirm"):
            if c.pressed("diagonal_modifier"):
                self.state.wait()  # LB＋A（Shift＋決定）は足踏み
            elif self.state.player_on_stairs:
                self._confirm_descend()
            else:
                self._execute_command("attack")
            return
        if c.triggered("wait"):
            self.state.wait()
            return

        if isinstance(direction_command, MoveCommand):
            self.state.move_player(direction_command.direction)
        elif isinstance(direction_command, TurnCommand):
            self.state.face(direction_command.direction)

    def _update_command_bar(self) -> None:
        c = self.controls
        if c.triggered("cancel") or c.triggered("command_bar"):
            self.mode = Mode.EXPLORE
        elif c.triggered_repeat("left"):
            self.command_bar.move(-1)
        elif c.triggered_repeat("right"):
            self.command_bar.move(1)
        elif c.triggered("confirm"):
            self.mode = Mode.EXPLORE
            self._execute_command(self.command_bar.selected.id)

    def _handle_click(self) -> bool:
        position = self.controls.clicked()
        index = hit_test(*position) if position is not None else None
        if index is None:
            return False
        self.command_bar.index = index
        self.mode = Mode.EXPLORE
        self._execute_command(COMMANDS[index].id)
        return True

    def _close_on(self, toggle_action: str) -> None:
        if self.controls.triggered("cancel") or self.controls.triggered(toggle_action):
            self.mode = Mode.EXPLORE

    def _update_dialog(self) -> None:
        if self.dialog is None or self.dialog.update(self.controls):
            self.dialog = None
            self.mode = Mode.EXPLORE

    def _execute_command(self, command_id: str) -> None:
        if command_id == "items":
            self.mode = Mode.INVENTORY
        elif command_id == "map":
            self.mode = Mode.FULL_MAP
        elif command_id == "cook" and not self.state.can_cook:
            self.state.log.add("焚き火のそばか、携帯コンロがないと料理できない。")
        else:
            self.state.log.add(f"「{command_label(command_id)}」は未実装です。")

    def _is_command_enabled(self, command_id: str) -> bool:
        return command_id != "cook" or self.state.can_cook

    def _confirm_descend(self) -> None:
        if not self.state.can_descend:
            self.state.log.add("これより下へは、まだ降りられない。")
            return
        self.dialog = ConfirmDialog("階段を降りますか？", self._descend)
        self.mode = Mode.CONFIRM

    def _descend(self) -> None:
        if self.state.descend():
            self.banner_frames = FLOOR_BANNER_SECONDS * config.FPS

    # --- draw ---

    def draw(self) -> None:
        pyxel.cls(0)
        if self.mode == Mode.FULL_MAP:
            minimap.draw_full_map(
                self.state.floor, self.state.fog, self.state.player.pos, self._floor_label()
            )
            return
        if self.mode == Mode.LOG_HISTORY:
            self.log_history.draw()
            return

        player = self.state.player
        self._draw_map()
        exp_next = exp_to_next_level(player.level, self.state.params.progression)
        hud.draw_status_bar(player, self._floor_label(), exp_next)
        self._draw_bottom_panel()
        if self.banner_frames > 0:
            self._draw_floor_banner()
        if self.show_debug:
            self._draw_debug()

        if self.mode == Mode.INVENTORY:
            draw_inventory(0, self.state.params.inventory_capacity)
        elif self.mode == Mode.CONFIRM and self.dialog is not None:
            self.dialog.draw()

    def _floor_label(self) -> str:
        return f"B{self.state.floor.number}F {self.state.area.name}"

    def _draw_map(self) -> None:
        ts = config.TILE_SIZE
        floor, fog, player = self.state.floor, self.state.fog, self.state.player
        view_w, view_h = config.MAP_VIEW_TILES_W, config.MAP_VIEW_TILES_H
        cam_x, cam_y = camera_origin(player.x, player.y, floor.width, floor.height, view_w, view_h)
        frame = pyxel.frame_count // config.ANIMATION_TICKS

        pyxel.clip(0, config.MAP_TOP, config.SCREEN_WIDTH, config.MAP_VIEW_HEIGHT)
        # 既知タイルを暗いパレットで描いてから、視界内のタイルを通常の色で描く
        for visibility in (Visibility.KNOWN, Visibility.VISIBLE):
            if visibility == Visibility.KNOWN:
                for src, dst in KNOWN_TILE_PALETTE.items():
                    pyxel.pal(src, dst)
            for ty in range(view_h):
                for tx in range(view_w):
                    mx, my = cam_x + tx, cam_y + ty
                    if fog.state(mx, my) != visibility:
                        continue
                    tile = floor.tile_at(mx, my)
                    # 部屋や通路に接していない岩盤は描かず、黒のままにする
                    if tile == Tile.WALL and not floor.is_edge_wall(mx, my):
                        continue
                    sx, sy = tx * ts, config.MAP_TOP + ty * ts
                    self.sprites.draw(self._tile_sprite(tile), sx, sy, frame, colkey=None)
            pyxel.pal()

        self.sprites.draw(
            player.sprite_name,
            (player.x - cam_x) * ts,
            config.MAP_TOP + (player.y - cam_y) * ts,
            frame,
        )
        pyxel.clip()

    def _tile_sprite(self, tile: Tile) -> str:
        """エリア別の素材（例: wall_moss）があればそれを、なければ共通の素材を使う。"""
        base = SPRITE_NAMES[tile]
        area_specific = f"{base}_{self.state.area.id}"
        return area_specific if self.sprites.has(area_specific) else base

    def _draw_bottom_panel(self) -> None:
        top = config.MAP_TOP + config.MAP_VIEW_HEIGHT
        pyxel.line(0, top, config.SCREEN_WIDTH - 1, top, COLOR_FRAME)
        self.command_bar.draw(
            focused=self.mode == Mode.COMMAND_BAR, is_enabled=self._is_command_enabled
        )
        draw_recent(self.state.log, top + 15)

    def _draw_floor_banner(self) -> None:
        label = self._floor_label()
        width = font.text_width(label)
        x = (config.SCREEN_WIDTH - width) // 2
        y = config.MAP_TOP + (config.MAP_VIEW_HEIGHT - config.TILE_SIZE) // 2
        pyxel.rect(x - 6, y - 4, width + 12, 16, 0)
        pyxel.rectb(x - 6, y - 4, width + 12, 16, COLOR_SUBTEXT)
        font.draw_text(x, y, label, COLOR_TEXT)

    def _draw_debug(self) -> None:
        s = self.state
        text = f"SEED {s.run_seed} TURN {s.turn} POS {s.player.x},{s.player.y}"
        width = font.text_width(text)
        x = config.SCREEN_WIDTH - width - 2
        pyxel.rect(x - 2, config.MAP_TOP, width + 4, 10, 0)
        font.draw_text(x, config.MAP_TOP + 1, text, COLOR_DEBUG)
