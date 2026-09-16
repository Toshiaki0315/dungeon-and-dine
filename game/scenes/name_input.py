"""名前入力画面。仕様書 6.1。

ゲームを始めるときに主人公の名前を入力する。何も入力しなければ「レオ」を使う。
Pyxel が受け取れるのは半角英数と記号のため、日本語の入力はできない。
"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.entities.player import PLAYER_NAME
from game.scenes import Scene
from game.systems.meta import NAME_MAX_LENGTH, MetaProgress
from game.ui import font
from game.ui.input import Controls
from game.ui.menu import draw_window
from game.ui.sprites import SpriteSheet

COLOR_TITLE = 10
COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_CURSOR = 7

BOX_X, BOX_Y, BOX_W, BOX_H = 72, 72, 176, 28
PICTURE_SCALE = 5
CURSOR_TICKS = 8


class NameInputScene:
    def __init__(
        self,
        *,
        controls: Controls,
        meta: MetaProgress,
        sprites: SpriteSheet,
        on_done: Callable[[str], Scene],
    ) -> None:
        self.controls = controls
        self.sprites = sprites
        self.on_done = on_done
        self.text = meta.player_name if meta.player_name != PLAYER_NAME else ""

    @property
    def name(self) -> str:
        """確定する名前。空のままなら既定の「レオ」。"""
        return self.text.strip() or PLAYER_NAME

    def update(self) -> Scene | None:
        if self.controls.triggered("confirm"):
            return self.on_done(self.name)
        if self.controls.triggered("cancel"):
            return self.on_done(PLAYER_NAME)
        if pyxel.btnp(pyxel.KEY_BACKSPACE, hold=20, repeat=3):
            self.text = self.text[:-1]
            return None
        self._type(pyxel.input_text)
        return None

    def _type(self, typed: str) -> None:
        """このフレームに入力された文字を受け取る（印字できる文字だけ）。"""
        for char in typed:
            if len(self.text) >= NAME_MAX_LENGTH:
                return
            if not char.isprintable() or (char == " " and not self.text):
                continue
            self.text += char

    def draw(self) -> None:
        pyxel.cls(0)
        font.draw_text_centered(24, "名前を入力してください", COLOR_TITLE)
        font.draw_text_centered(40, f"（半角英数{NAME_MAX_LENGTH}文字まで）", COLOR_SUBTEXT)

        draw_window(BOX_X, BOX_Y, BOX_W, BOX_H)
        text_x = BOX_X + 12
        font.draw_text(text_x, BOX_Y + 10, self.text, COLOR_TEXT)
        if (pyxel.frame_count // CURSOR_TICKS) % 2 == 0:
            cursor_x = text_x + font.text_width(self.text)
            pyxel.rect(cursor_x + 1, BOX_Y + 9, 4, 8, COLOR_CURSOR)

        if not self.text:
            font.draw_text_centered(
                BOX_Y + BOX_H + 8, f"未入力なら「{PLAYER_NAME}」", COLOR_SUBTEXT
            )
        frame = pyxel.frame_count // config.ANIMATION_TICKS
        self.sprites.draw_scaled("leo_down", 24, 60, PICTURE_SCALE, frame)
        font.draw_text_centered(
            config.SCREEN_HEIGHT - 16,
            "Enter: 決定　Backspace: 1文字消す　Esc: 既定の名前",
            COLOR_SUBTEXT,
        )
