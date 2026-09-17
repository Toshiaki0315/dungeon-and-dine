"""調理画面（食材選択ウィンドウ）。仕様書 14章。

料理カットインの背景の上に重ねて表示する。左に材料の候補、右に選んだ材料を並べる。
"""

from __future__ import annotations

import pyxel

from game import config
from game.entities.item import ItemInstance
from game.systems.cooking import MAX_MATERIALS, MIN_MATERIALS
from game.systems.game_state import GameState
from game.ui import font
from game.ui.input import Controls
from game.ui.menu import draw_window

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_LINE = 5
COLOR_CURSOR = 5
COLOR_NUMBER = 10  # 選んだ材料の番号
COLOR_DISH = 11  # 手帳にある料理の予告
COLOR_FAILURE = 8  # 失敗リストにある組み合わせ

CANCELLED = "cancelled"  # update() の戻り値: 調理をやめる

LIST_X, LIST_Y, LIST_W, LIST_H = 12, 12, 372, 256
PANEL_X, PANEL_W = 396, 232
ROWS = 9
COOK_LABEL = "［調理する］"


class CookingView:
    def __init__(self, state: GameState) -> None:
        self.state = state
        self.cursor = 0
        self.scroll = 0
        self.selected: list[ItemInstance] = []
        self.message = ""

    def open(self) -> None:
        self.cursor = 0
        self.scroll = 0
        self.selected = []
        self.message = ""

    @property
    def candidates(self) -> list[ItemInstance]:
        return self.state.cooking_candidates()

    def update(self, controls: Controls) -> list[ItemInstance] | str | None:
        """材料が決まったらその一覧、やめるなら CANCELLED、それ以外は None を返す。"""
        if controls.triggered("cancel"):
            return CANCELLED
        rows = len(self.candidates) + 1  # 最後の行は「調理する」
        if controls.triggered_repeat("up"):
            self.cursor = (self.cursor - 1) % rows
            self.message = ""
        elif controls.triggered_repeat("down"):
            self.cursor = (self.cursor + 1) % rows
            self.message = ""
        elif controls.triggered("confirm"):
            return self._confirm()
        elif controls.triggered("cook"):
            return self._cook()
        self._clamp()
        return None

    def _confirm(self) -> list[ItemInstance] | None:
        candidates = self.candidates
        if self.cursor >= len(candidates):
            return self._cook()
        item = candidates[self.cursor]
        if item in self.selected:
            self.selected.remove(item)
            self.message = ""
        elif len(self.selected) >= MAX_MATERIALS:
            self.message = f"材料は{MAX_MATERIALS}つまで。"
        else:
            self.selected.append(item)
            self.message = ""
        return None

    def _cook(self) -> list[ItemInstance] | None:
        if MIN_MATERIALS <= len(self.selected) <= MAX_MATERIALS:
            return list(self.selected)
        self.message = f"材料を{MIN_MATERIALS}〜{MAX_MATERIALS}個選んでください。"
        return None

    def _clamp(self) -> None:
        rows = len(self.candidates) + 1
        self.cursor = max(0, min(self.cursor, rows - 1))
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + ROWS:
            self.scroll = self.cursor - ROWS + 1
        self.scroll = max(0, min(self.scroll, max(0, rows - ROWS)))

    # --- 描画 ---

    def draw(self) -> None:
        self._draw_list()
        self._draw_panel()

    def _draw_list(self) -> None:
        x, y, w, h = LIST_X, LIST_Y, LIST_W, LIST_H
        draw_window(x, y, w, h)
        font.draw_text(x + 16, y + 10, "材料を選ぶ", COLOR_TEXT)
        pyxel.line(x + 8, y + 30, x + w - 10, y + 30, COLOR_LINE)

        candidates = self.candidates
        rows: list[tuple[str, ItemInstance | None]] = [(i.name, i) for i in candidates]
        rows.append((COOK_LABEL, None))
        if not candidates:
            font.draw_text(x + 16, y + 38, "材料にできるものがない。", COLOR_SUBTEXT)
        for row, (label, item) in enumerate(rows[self.scroll : self.scroll + ROWS]):
            index = self.scroll + row
            row_y = y + 38 + row * config.LINE_HEIGHT
            if index == self.cursor:
                pyxel.rect(x + 8, row_y - 2, w - 16, config.LINE_HEIGHT, COLOR_CURSOR)
            if item is not None and item in self.selected:
                number = self.selected.index(item) + 1
                font.draw_text(x + 12, row_y, str(number), COLOR_NUMBER)
            color = (
                COLOR_TEXT
                if item is not None or len(self.selected) >= MIN_MATERIALS
                else COLOR_SUBTEXT
            )
            font.draw_text(x + 32, row_y, label, color)
        if self.scroll > 0:
            font.draw_text(x + w - 24, y + 38, "▲", COLOR_SUBTEXT)
        if self.scroll + ROWS < len(rows):
            font.draw_text(x + w - 24, y + 38 + (ROWS - 1) * config.LINE_HEIGHT, "▼", COLOR_SUBTEXT)

    def _draw_panel(self) -> None:
        x, y, w = PANEL_X, LIST_Y, PANEL_W
        draw_window(x, y, w, LIST_H)
        font.draw_text(x + 16, y + 10, "選んだ材料", COLOR_TEXT)
        pyxel.line(x + 8, y + 30, x + w - 10, y + 30, COLOR_LINE)
        for slot in range(MAX_MATERIALS):
            row_y = y + 40 + slot * config.LINE_HEIGHT
            if slot < len(self.selected):
                font.draw_text(x + 12, row_y, f"{slot + 1}", COLOR_NUMBER)
                font.draw_text(x + 32, row_y, self.selected[slot].name, COLOR_TEXT)
            else:
                font.draw_text(x + 32, row_y, "――", COLOR_SUBTEXT)

        preview = self.state.cooking_preview(self.selected)
        preview_y = y + 44 + MAX_MATERIALS * config.LINE_HEIGHT
        if preview.dish_name is not None:
            font.draw_text(x + 16, preview_y, f"→ {preview.dish_name}", COLOR_DISH)
        elif preview.known_failure:
            font.draw_text(x + 16, preview_y, "✕ 失敗した組み合わせ", COLOR_FAILURE)
        elif len(self.selected) >= MIN_MATERIALS:
            font.draw_text(x + 16, preview_y, "→ ？？？", COLOR_SUBTEXT)
        if self.message:
            font.draw_text(x + 16, preview_y + config.LINE_HEIGHT, self.message, COLOR_FAILURE)
