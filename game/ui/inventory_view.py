"""インベントリ画面とアイテムメニュー。仕様書 11.1 / 14章。"""

from __future__ import annotations

from dataclasses import dataclass

import pyxel

from game import config
from game.entities.item import ItemInstance
from game.systems.inventory import Inventory
from game.ui import font
from game.ui.input import Controls
from game.ui.log import wrap_text
from game.ui.menu import draw_window

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_LINE = 5
COLOR_CURSOR = 5

ACTION_USE = "use"
ACTION_THROW = "throw"
ACTION_DROP = "drop"
ACTION_DESCRIBE = "describe"

LIST_X, LIST_Y, LIST_W, LIST_H = 24, config.MAP_TOP + 2, 196, 116
ROWS = 8


@dataclass(frozen=True)
class ItemRequest:
    """インベントリ画面で選ばれた操作。"""

    kind: str  # "use" | "throw" | "drop"
    item: ItemInstance


class InventoryView:
    def __init__(self, inventory: Inventory) -> None:
        self.inventory = inventory
        self.cursor = 0
        self.scroll = 0
        self.menu: list[tuple[str, str]] | None = None
        self.menu_cursor = 0
        self.describing = False

    @property
    def selected(self) -> ItemInstance | None:
        items = self.inventory.items
        return items[self.cursor] if 0 <= self.cursor < len(items) else None

    def open(self) -> None:
        self.menu = None
        self.describing = False
        self._clamp()

    def update(self, controls: Controls) -> ItemRequest | bool | None:
        """選ばれた操作、閉じるなら True、それ以外は None を返す。"""
        if self.describing:
            if controls.triggered("confirm") or controls.triggered("cancel"):
                self.describing = False
            return None
        if self.menu is not None:
            return self._update_menu(controls)

        if controls.triggered("cancel") or controls.triggered("inventory"):
            return True
        item = self.selected
        if item is None:
            return None
        if controls.triggered_repeat("up"):
            self.cursor = (self.cursor - 1) % len(self.inventory.items)
        elif controls.triggered_repeat("down"):
            self.cursor = (self.cursor + 1) % len(self.inventory.items)
        elif controls.triggered("confirm"):
            self.menu = self._menu_for(item)
            self.menu_cursor = 0
        self._clamp()
        return None

    def _update_menu(self, controls: Controls) -> ItemRequest | None:
        assert self.menu is not None
        item = self.selected
        if controls.triggered("cancel") or item is None:
            self.menu = None
        elif controls.triggered_repeat("up"):
            self.menu_cursor = (self.menu_cursor - 1) % len(self.menu)
        elif controls.triggered_repeat("down"):
            self.menu_cursor = (self.menu_cursor + 1) % len(self.menu)
        elif controls.triggered("confirm"):
            action = self.menu[self.menu_cursor][0]
            self.menu = None
            if action == ACTION_DESCRIBE:
                self.describing = True
            else:
                return ItemRequest(action, item)
        return None

    @staticmethod
    def _menu_for(item: ItemInstance) -> list[tuple[str, str]]:
        menu: list[tuple[str, str]] = []
        if item.definition.use_label is not None:
            menu.append((ACTION_USE, item.definition.use_label))
        # 装備する／外す はフェーズ4で追加する
        menu += [(ACTION_THROW, "投げる"), (ACTION_DROP, "捨てる"), (ACTION_DESCRIBE, "説明")]
        return menu

    def _clamp(self) -> None:
        count = len(self.inventory.items)
        self.cursor = max(0, min(self.cursor, count - 1))
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + ROWS:
            self.scroll = self.cursor - ROWS + 1
        self.scroll = max(0, min(self.scroll, max(0, count - ROWS)))

    # --- 描画 ---

    def draw(self) -> None:
        x, y, w, h = LIST_X, LIST_Y, LIST_W, LIST_H
        draw_window(x, y, w, h)
        font.draw_text(x + 8, y + 5, "道具", COLOR_TEXT)
        count = f"{len(self.inventory)}/{self.inventory.capacity}"
        font.draw_text(x + w - 8 - font.text_width(count), y + 5, count, COLOR_TEXT)
        pyxel.line(x + 4, y + 15, x + w - 5, y + 15, COLOR_LINE)

        items = self.inventory.items
        if not items:
            font.draw_text(x + 8, y + 20, "何も持っていない。", COLOR_SUBTEXT)
        for row, item in enumerate(items[self.scroll : self.scroll + ROWS]):
            index = self.scroll + row
            row_y = y + 19 + row * config.LINE_HEIGHT
            if index == self.cursor:
                pyxel.rect(x + 4, row_y - 1, w - 8, config.LINE_HEIGHT, COLOR_CURSOR)
            font.draw_text(x + 8, row_y, item.name, COLOR_TEXT)
        if self.scroll > 0:
            font.draw_text(x + w - 12, y + 19, "▲", COLOR_SUBTEXT)
        if self.scroll + ROWS < len(items):
            font.draw_text(x + w - 12, y + 19 + (ROWS - 1) * config.LINE_HEIGHT, "▼", COLOR_SUBTEXT)
        font.draw_text(x + 8, y + h - 11, "決定: メニュー  I / Esc: 閉じる", COLOR_SUBTEXT)

        if self.menu is not None:
            self._draw_menu()
        if self.describing and self.selected is not None:
            self._draw_description(self.selected)

    def _draw_menu(self) -> None:
        assert self.menu is not None
        x, y = LIST_X + LIST_W + 4, LIST_Y
        w, h = 68, 8 + len(self.menu) * config.LINE_HEIGHT
        draw_window(x, y, w, h)
        for i, (_, label) in enumerate(self.menu):
            row_y = y + 4 + i * config.LINE_HEIGHT
            if i == self.menu_cursor:
                pyxel.rect(x + 3, row_y - 1, w - 6, config.LINE_HEIGHT, COLOR_CURSOR)
            font.draw_text(x + 8, row_y, label, COLOR_TEXT)

    def _draw_description(self, item: ItemInstance) -> None:
        w = config.SCREEN_WIDTH - 48
        lines = wrap_text(item.definition.description, w - 16, font.text_width)
        h = 22 + len(lines) * config.LINE_HEIGHT
        x = 24
        y = config.MAP_TOP + (config.MAP_VIEW_HEIGHT - h) // 2
        draw_window(x, y, w, h)
        font.draw_text(x + 8, y + 6, item.name, COLOR_TEXT)
        for i, line in enumerate(lines):
            font.draw_text(x + 8, y + 18 + i * config.LINE_HEIGHT, line, COLOR_SUBTEXT)
