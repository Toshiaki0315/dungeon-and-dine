"""汎用のウィンドウと確認ダイアログ。仕様書 14章。"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.ui import font
from game.ui.input import Controls

COLOR_WINDOW_BG = 0
COLOR_WINDOW_FRAME = 13
COLOR_TEXT = 7
COLOR_CURSOR = 5


def draw_window(x: int, y: int, w: int, h: int) -> None:
    pyxel.rect(x, y, w, h, COLOR_WINDOW_BG)
    pyxel.rectb(x, y, w, h, COLOR_WINDOW_FRAME)


class ConfirmDialog:
    """「はい／いいえ」の確認ダイアログ。"""

    OPTIONS: tuple[str, str] = ("はい", "いいえ")

    def __init__(self, message: str, on_yes: Callable[[], None]) -> None:
        self.message = message
        self.on_yes = on_yes
        self.selected = 0

    def update(self, controls: Controls) -> bool:
        """ダイアログを閉じたら True を返す。"""
        if controls.triggered("cancel"):
            return True
        if any(controls.triggered_repeat(a) for a in ("left", "right", "up", "down")):
            self.selected = 1 - self.selected
        elif controls.triggered("confirm"):
            if self.selected == 0:
                self.on_yes()
            return True
        return False

    def draw(self) -> None:
        w = max(font.text_width(self.message) + 24, 120)
        h = 40
        x = (config.SCREEN_WIDTH - w) // 2
        y = config.MAP_TOP + (config.MAP_VIEW_HEIGHT - h) // 2
        draw_window(x, y, w, h)
        font.draw_text_centered(y + 8, self.message, COLOR_TEXT)
        for i, label in enumerate(self.OPTIONS):
            ox = config.SCREEN_WIDTH // 2 - 36 + i * 48
            if i == self.selected:
                pyxel.rect(ox - 4, y + 22, font.text_width(label) + 8, 12, COLOR_CURSOR)
            font.draw_text(ox, y + 24, label, COLOR_TEXT)
