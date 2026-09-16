"""レシピ手帳画面。仕様書 9.6。

発見済みのレシピと、失敗した組み合わせを一覧で表示する。未発見のレシピは ？？？ と表示する。
"""

from __future__ import annotations

import pyxel

from game import config
from game.systems.cooking import describe_effects
from game.systems.game_state import GameState
from game.ui import font
from game.ui.input import Controls
from game.ui.menu import draw_window

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_LINE = 5
COLOR_TAB = 5
COLOR_UNKNOWN = 13
COLOR_FAILURE = 8

X, Y, W, H = 12, config.MAP_TOP + 2, 296, 116
TABS = ("レシピ", "失敗リスト")
ENTRY_ROWS = 4  # 1ページに表示するレシピの数（1件2行）


class NotebookView:
    def __init__(self, state: GameState) -> None:
        self.state = state
        self.tab = 0
        self.scroll = 0

    def open(self) -> None:
        self.tab = 0
        self.scroll = 0

    def update(self, controls: Controls) -> bool:
        """閉じたら True を返す。"""
        if controls.triggered("cancel") or controls.triggered("notebook"):
            return True
        if controls.triggered_repeat("left") or controls.triggered_repeat("right"):
            self.tab = 1 - self.tab
            self.scroll = 0
        elif controls.triggered_repeat("down"):
            self.scroll = min(self._max_scroll(), self.scroll + 1)
        elif controls.triggered_repeat("up"):
            self.scroll = max(0, self.scroll - 1)
        return False

    def _entries(self) -> int:
        if self.tab == 0:
            return len(self.state.catalog.recipes)
        return len(self.state.notebook.failures)

    def _max_scroll(self) -> int:
        rows = ENTRY_ROWS if self.tab == 0 else ENTRY_ROWS * 2
        return max(0, self._entries() - rows)

    # --- 描画 ---

    def draw(self) -> None:
        draw_window(X, Y, W, H)
        notebook = self.state.notebook
        total = len(self.state.catalog.recipes)
        title = f"レシピ手帳  発見 {len(notebook.discovered)}/{total}"
        font.draw_text(X + 8, Y + 5, title, COLOR_TEXT)
        for i, label in enumerate(TABS):
            tab_x = X + W - 130 + i * 64
            if i == self.tab:
                pyxel.rect(tab_x - 4, Y + 4, font.text_width(label) + 8, 10, COLOR_TAB)
            font.draw_text(tab_x, Y + 5, label, COLOR_TEXT)
        pyxel.line(X + 4, Y + 15, X + W - 5, Y + 15, COLOR_LINE)

        if self.tab == 0:
            self._draw_recipes()
        else:
            self._draw_failures()
        hint = "←→: 切り替え  ↑↓: スクロール  R / Esc: 閉じる"
        font.draw_text(X + 8, Y + H - 11, hint, COLOR_SUBTEXT)

    def _draw_recipes(self) -> None:
        catalog = self.state.catalog
        notebook = self.state.notebook
        status_names = {s.id: s.name for s in catalog.statuses.values()}
        recipes = list(catalog.recipes.values())[self.scroll : self.scroll + ENTRY_ROWS]
        for row, recipe in enumerate(recipes):
            y = Y + 19 + row * config.LINE_HEIGHT * 2
            if not notebook.is_discovered(recipe.id):
                font.draw_text(X + 8, y, "？？？", COLOR_UNKNOWN)
                continue
            font.draw_text(X + 8, y, recipe.name, COLOR_TEXT)
            font.draw_text(X + 120, y, catalog.ingredient_label(recipe), COLOR_SUBTEXT)
            effects = describe_effects(recipe.effects, status_names)
            font.draw_text(X + 16, y + config.LINE_HEIGHT, effects, COLOR_SUBTEXT)

    def _draw_failures(self) -> None:
        catalog = self.state.catalog
        failures = self.state.notebook.failures
        if not failures:
            font.draw_text(X + 8, Y + 19, "まだ失敗していない。", COLOR_SUBTEXT)
            return
        rows = ENTRY_ROWS * 2
        for row, key in enumerate(failures[self.scroll : self.scroll + rows]):
            y = Y + 19 + row * config.LINE_HEIGHT
            names = "＋".join(catalog.items[item_id].name for item_id in key)
            font.draw_text(X + 8, y, "✕", COLOR_FAILURE)
            font.draw_text(X + 20, y, names, COLOR_SUBTEXT)
