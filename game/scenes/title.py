"""タイトル画面（はじめる／つづきから）。仕様書 4章・14章。"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.scenes import Scene
from game.systems.meta import MetaProgress
from game.ui import font
from game.ui.input import Controls
from game.ui.sprites import SpriteSheet

COLOR_TITLE = 10
COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_CURSOR = 5

MENU_X, MENU_Y = 32, 88
PICTURE_X, PICTURE_Y, PICTURE_SCALE = 200, 60, 6


class TitleScene:
    def __init__(
        self,
        *,
        controls: Controls,
        sprites: SpriteSheet,
        meta: MetaProgress,
        start: Callable[[], Scene],
        resume: Callable[[], Scene | None],
        quit_game: Callable[[], None],
        has_run: bool,
    ) -> None:
        self.controls = controls
        self.sprites = sprites
        self.meta = meta
        self.quit_game = quit_game
        self.cursor = 0
        self.message = ""
        self.options: list[tuple[str, Callable[[], Scene | None]]] = [("はじめる", start)]
        if has_run:
            self.options.append(("つづきから", resume))
        self.options.append(("おわる", self._quit))

    def _quit(self) -> Scene | None:
        self.quit_game()
        return None

    def update(self) -> Scene | None:
        c = self.controls
        if c.triggered_repeat("up"):
            self.cursor = (self.cursor - 1) % len(self.options)
        elif c.triggered_repeat("down"):
            self.cursor = (self.cursor + 1) % len(self.options)
        elif c.triggered("confirm"):
            scene = self.options[self.cursor][1]()
            if scene is not None:
                return scene
            self.message = "つづきのデータがない。"
        return None

    def draw(self) -> None:
        pyxel.cls(0)
        font.draw_text_centered(28, "Dungeon & Dine", COLOR_TITLE)
        font.draw_text_centered(44, "飢餓のトレジャーハンター", COLOR_SUBTEXT)

        for i, (label, _) in enumerate(self.options):
            y = MENU_Y + i * 14
            if i == self.cursor:
                pyxel.rect(MENU_X - 6, y - 2, 100, 12, COLOR_CURSOR)
            font.draw_text(MENU_X, y, label, COLOR_TEXT)

        frame = pyxel.frame_count // 5
        self.sprites.draw_scaled("campfire", PICTURE_X, PICTURE_Y, PICTURE_SCALE, frame)

        record = f"最深到達 B{self.meta.deepest_floor}F　クリア {self.meta.clears}回"
        font.draw_text_centered(config.SCREEN_HEIGHT - 24, record, COLOR_SUBTEXT)
        if self.message:
            font.draw_text_centered(config.SCREEN_HEIGHT - 12, self.message, COLOR_TEXT)
