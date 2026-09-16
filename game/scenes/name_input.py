"""名前入力画面。仕様書 6.1。

ゲームを始めるときに主人公の名前を入力する。何も入力しなければ「レオ」を使う。
五十音表から選ぶ方式にして、日本語（ひらがな・カタカナ）も入力できるようにしている。
キーボードからの半角英数の直接入力も受け付ける。
"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.entities.player import PLAYER_NAME
from game.scenes import Scene
from game.systems.meta import NAME_MAX_LENGTH, MetaProgress
from game.ui import font, kana
from game.ui.input import Controls
from game.ui.menu import draw_window
from game.ui.sprites import SpriteSheet

COLOR_TITLE = 10
COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_CURSOR = 5
COLOR_CARET = 7

BOX_X, BOX_Y, BOX_W, BOX_H = 92, 26, 136, 20
GRID_X, GRID_Y = 26, 54
CELL_W, CELL_H = 18, 13
ACTION_Y = GRID_Y + 6 * CELL_H + 4
CARET_TICKS = 8

# 表の下に並べるボタン（ラベル, 動作）
ACTION_MARK = "mark"
ACTION_SEMI = "semi"
ACTION_DELETE = "delete"
ACTION_PAGE = "page"
ACTION_DONE = "done"
ACTIONS: tuple[tuple[str, str], ...] = (
    ("゛", ACTION_MARK),
    ("゜", ACTION_SEMI),
    ("けす", ACTION_DELETE),
    ("かな/英数", ACTION_PAGE),
    ("けってい", ACTION_DONE),
)


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
        self.page = 0
        self.row = 0
        self.column = 0
        self.on_actions = False  # カーソルが下のボタン列にあるか
        self.action = 0

    @property
    def name(self) -> str:
        """確定する名前。空のままなら既定の「レオ」。"""
        return self.text.strip() or PLAYER_NAME

    @property
    def grid(self) -> kana.Grid:
        return kana.grid_for(self.page)

    # --- 更新 ---

    def update(self) -> Scene | None:
        c = self.controls
        if c.triggered("cancel"):
            return self.on_done(PLAYER_NAME)
        if pyxel.btnp(pyxel.KEY_BACKSPACE, hold=20, repeat=3):
            self.text = self.text[:-1]
            return None
        self._type(pyxel.input_text)  # キーボードからの半角入力
        self._move_cursor()
        if c.triggered("confirm"):
            return self._press()
        return None

    def _move_cursor(self) -> None:
        c = self.controls
        dx = int(c.triggered_repeat("right")) - int(c.triggered_repeat("left"))
        dy = int(c.triggered_repeat("down")) - int(c.triggered_repeat("up"))
        if dx == 0 and dy == 0:
            return
        if self.on_actions:
            if dy < 0:
                self.on_actions = False  # 表へ戻る
            else:
                self.action = (self.action + dx) % len(ACTIONS)
            return
        rows = len(self.grid)
        if dy > 0 and self.row == rows - 1:
            self.on_actions = True  # 表の下からボタン列へ
            return
        self.row, self.column = kana.move(self.grid, self.row, self.column, dx, dy)

    def _press(self) -> Scene | None:
        if not self.on_actions:
            self._append(kana.char_at(self.grid, self.row, self.column))
            return None
        action = ACTIONS[self.action][1]
        if action == ACTION_DONE:
            return self.on_done(self.name)
        if action == ACTION_DELETE:
            self.text = self.text[:-1]
        elif action == ACTION_MARK:
            self.text = kana.apply_mark(self.text)
        elif action == ACTION_SEMI:
            self.text = kana.apply_mark(self.text, semi=True)
        elif action == ACTION_PAGE:
            self.page = (self.page + 1) % len(kana.PAGES)
            self.row = min(self.row, len(self.grid) - 1)
        return None

    def _append(self, char: str) -> None:
        if char and len(self.text) < NAME_MAX_LENGTH:
            self.text += char

    def _type(self, typed: str) -> None:
        """キーボードから打った文字（半角）を受け取る。"""
        for char in typed:
            if not char.isprintable() or (char == " " and not self.text):
                continue
            self._append(char)

    # --- 描画 ---

    def draw(self) -> None:
        pyxel.cls(0)
        font.draw_text(8, 6, "名前を入力してください", COLOR_TITLE)
        count = f"{len(self.text)}/{NAME_MAX_LENGTH}"
        font.draw_text(config.SCREEN_WIDTH - 8 - font.text_width(count), 6, count, COLOR_SUBTEXT)

        self._draw_name_box()
        self._draw_grid()
        self._draw_actions()
        frame = pyxel.frame_count // config.ANIMATION_TICKS
        self.sprites.draw_scaled("leo_down", 20, 20, 4, frame)
        hint = "↑↓←→: 選ぶ  決定: 入力  Esc: 既定の名前"
        font.draw_text_centered(config.SCREEN_HEIGHT - 9, hint, COLOR_SUBTEXT)

    def _draw_name_box(self) -> None:
        draw_window(BOX_X, BOX_Y, BOX_W, BOX_H)
        text_x = BOX_X + 8
        font.draw_text(text_x, BOX_Y + 6, self.text, COLOR_TEXT)
        if (pyxel.frame_count // CARET_TICKS) % 2 == 0:
            pyxel.rect(text_x + font.text_width(self.text) + 1, BOX_Y + 5, 4, 8, COLOR_CARET)
        if not self.text:
            font.draw_text(BOX_X + BOX_W + 6, BOX_Y + 6, f"未入力: {PLAYER_NAME}", COLOR_SUBTEXT)

    def _draw_grid(self) -> None:
        for row_index, row in enumerate(self.grid):
            for column, char in enumerate(row):
                x = GRID_X + column * CELL_W
                y = GRID_Y + row_index * CELL_H
                selected = not self.on_actions and row_index == self.row and column == self.column
                if selected:
                    pyxel.rect(x - 2, y - 2, CELL_W - 2, CELL_H - 2, COLOR_CURSOR)
                if char != kana.FULL_WIDTH_SPACE:
                    font.draw_text(x, y, char, COLOR_TEXT)

    def _draw_actions(self) -> None:
        x = GRID_X
        for index, (label, _) in enumerate(ACTIONS):
            width = font.text_width(label) + 8
            if self.on_actions and index == self.action:
                pyxel.rect(x - 2, ACTION_Y - 2, width, 12, COLOR_CURSOR)
            else:
                pyxel.rectb(x - 2, ACTION_Y - 2, width, 12, COLOR_SUBTEXT)
            font.draw_text(x + 2, ACTION_Y + 1, label, COLOR_TEXT)
            x += width + 4
        page = kana.page_name(self.page)
        font.draw_text(x + 4, ACTION_Y + 1, f"（{page}）", COLOR_SUBTEXT)
