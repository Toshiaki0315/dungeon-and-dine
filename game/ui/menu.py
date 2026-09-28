"""汎用のウィンドウと確認ダイアログ。仕様書 14章。"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.ui import font, mouse
from game.ui.input import Controls

COLOR_WINDOW_BG = 0
COLOR_WINDOW_FRAME = 13
COLOR_TEXT = 7
COLOR_CURSOR = 5


def draw_window(x: int, y: int, w: int, h: int) -> None:
    pyxel.rect(x, y, w, h, COLOR_WINDOW_BG)
    pyxel.rectb(x, y, w, h, COLOR_WINDOW_FRAME)


class ConfirmDialog:
    """「はい／いいえ」の確認ダイアログ。on_yes の戻り値は使わない。"""

    OPTIONS: tuple[str, str] = ("はい", "いいえ")

    def __init__(self, message: str, on_yes: Callable[[], object]) -> None:
        self.message = message
        self.on_yes = on_yes
        self.selected = 0

    def _layout(self) -> tuple[int, int, int, int]:
        """ウィンドウの位置と大きさ（描画とクリック判定で同じ値を使う）。"""
        w = max(font.text_width(self.message) + 48, 240)
        h = 80
        return (
            (config.SCREEN_WIDTH - w) // 2,
            config.MAP_TOP + (config.MAP_VIEW_HEIGHT - h) // 2,
            w,
            h,
        )

    def option_rects(self) -> list[mouse.Rect]:
        y = self._layout()[1]
        return [
            (config.SCREEN_WIDTH // 2 - 80 + i * 96, y + 44, font.text_width(label) + 16, 24)
            for i, label in enumerate(self.OPTIONS)
        ]

    def update(self, controls: Controls) -> bool:
        """ダイアログを閉じたら True を返す。"""
        if controls.triggered("cancel") or controls.right_clicked():
            return True
        click = controls.clicked()
        if click is not None:
            index = mouse.index_of(click, self.option_rects())
            if index is not None:
                self.selected = index
                if index == 0:
                    self.on_yes()
                return True
            return False
        if any(controls.triggered_repeat(a) for a in ("left", "right", "up", "down")):
            self.selected = 1 - self.selected
        elif controls.triggered("confirm"):
            if self.selected == 0:
                self.on_yes()
            return True
        return False

    def draw(self) -> None:
        x, y, w, h = self._layout()
        draw_window(x, y, w, h)
        font.draw_text_centered(y + 16, self.message, COLOR_TEXT)
        for i, (label, rect) in enumerate(zip(self.OPTIONS, self.option_rects(), strict=True)):
            if i == self.selected:
                pyxel.rect(*rect, COLOR_CURSOR)
            font.draw_text(rect[0] + 8, y + 48, label, COLOR_TEXT)
