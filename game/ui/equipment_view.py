"""装備画面。仕様書 14章。

5つの部位と、装備による攻撃力・防御力の変化を表示する。未鑑定の装備の性能は「?」と表示する。
"""

from __future__ import annotations

from dataclasses import dataclass

import pyxel

from game import config
from game.entities.item import SLOT_NAMES, SLOTS, ItemInstance
from game.systems.game_state import GameState
from game.ui import font
from game.ui.input import Controls
from game.ui.inventory_view import draw_item_row
from game.ui.menu import draw_window

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_LINE = 5
COLOR_CURSOR = 5
COLOR_UP = 11
COLOR_DOWN = 8

X, Y, W, H = 24, config.MAP_TOP + 2, 272, 116
CHOICE_X, CHOICE_W = X + 118, 150
CHOICE_ROWS = 7


@dataclass(frozen=True)
class EquipRequest:
    slot: str
    item: ItemInstance | None  # None は「外す」


class EquipmentView:
    def __init__(self, state: GameState) -> None:
        self.state = state
        self.slot_cursor = 0
        self.choosing = False
        self.choice_cursor = 0

    @property
    def slot(self) -> str:
        return SLOTS[self.slot_cursor]

    def open(self) -> None:
        self.choosing = False

    def choices(self) -> list[ItemInstance | None]:
        """選んだ部位に付け替えられるもの（装備中なら先頭に「外す」）。"""
        current = self.state.player.equipment[self.slot]
        items = [
            i
            for i in self.state.inventory.items
            if i.definition.slot == self.slot and i is not current
        ]
        return ([None] if current is not None else []) + list(items)

    def update(self, controls: Controls) -> EquipRequest | bool | None:
        """付け替えの要求、閉じるなら True、それ以外は None を返す。"""
        if not self.choosing:
            if controls.triggered("cancel") or controls.triggered("equipment"):
                return True
            if controls.triggered_repeat("up"):
                self.slot_cursor = (self.slot_cursor - 1) % len(SLOTS)
            elif controls.triggered_repeat("down"):
                self.slot_cursor = (self.slot_cursor + 1) % len(SLOTS)
            elif controls.triggered("confirm") and self.choices():
                self.choosing = True
                self.choice_cursor = 0
            return None

        choices = self.choices()
        if controls.triggered("cancel") or not choices:
            self.choosing = False
        elif controls.triggered_repeat("up"):
            self.choice_cursor = (self.choice_cursor - 1) % len(choices)
        elif controls.triggered_repeat("down"):
            self.choice_cursor = (self.choice_cursor + 1) % len(choices)
        elif controls.triggered("confirm"):
            self.choosing = False
            return EquipRequest(self.slot, choices[self.choice_cursor])
        return None

    # --- 描画 ---

    def draw(self) -> None:
        draw_window(X, Y, W, H)
        font.draw_text(X + 8, Y + 5, "装備", COLOR_TEXT)
        pyxel.line(X + 4, Y + 15, X + W - 5, Y + 15, COLOR_LINE)

        equipment = self.state.player.equipment
        for i, slot in enumerate(SLOTS):
            row_y = Y + 20 + i * (config.LINE_HEIGHT + 2)
            if i == self.slot_cursor:
                color = COLOR_CURSOR if not self.choosing else 1
                pyxel.rect(X + 4, row_y - 1, W - 8, config.LINE_HEIGHT, color)
            font.draw_text(X + 8, row_y, SLOT_NAMES[slot], COLOR_SUBTEXT)
            item = equipment[slot]
            if item is None:
                font.draw_text(X + 32, row_y, "―", COLOR_SUBTEXT)
            else:
                draw_item_row(X + 26, row_y, item, equipped=False)

        stats = self.state.player_combat_stats()
        pyxel.line(X + 4, Y + H - 26, X + W - 5, Y + H - 26, COLOR_LINE)
        font.draw_text(X + 8, Y + H - 22, f"攻撃力 {stats.atk}  防御力 {stats.defense}", COLOR_TEXT)
        hint = "決定: 付け替える  Esc: 戻る" if self.choosing else "決定: 選ぶ  E / Esc: 閉じる"
        font.draw_text(X + 8, Y + H - 11, hint, COLOR_SUBTEXT)

        if self.choosing:
            self._draw_choices()

    def _draw_choices(self) -> None:
        choices = self.choices()
        h = 26 + min(len(choices), CHOICE_ROWS) * config.LINE_HEIGHT
        y = Y + 16
        draw_window(CHOICE_X, y, CHOICE_W, h)
        start = max(0, self.choice_cursor - CHOICE_ROWS + 1)
        for row, choice in enumerate(choices[start : start + CHOICE_ROWS]):
            row_y = y + 4 + row * config.LINE_HEIGHT
            if start + row == self.choice_cursor:
                pyxel.rect(CHOICE_X + 3, row_y - 1, CHOICE_W - 6, config.LINE_HEIGHT, COLOR_CURSOR)
            if choice is None:
                font.draw_text(CHOICE_X + 8, row_y, "（外す）", COLOR_TEXT)
            else:
                draw_item_row(CHOICE_X + 4, row_y, choice, equipped=False)

        # 付け替えたときの攻撃力・防御力（未鑑定なら ? ）
        current = self.state.player_combat_stats()
        preview = self.state.preview_stats(self.slot, choices[self.choice_cursor])
        preview_y = y + h - 12
        font.draw_text(CHOICE_X + 8, preview_y, "攻", COLOR_SUBTEXT)
        font.draw_text(CHOICE_X + 76, preview_y, "防", COLOR_SUBTEXT)
        if preview is None:
            font.draw_text(CHOICE_X + 20, preview_y, f"{current.atk}→?", COLOR_TEXT)
            font.draw_text(CHOICE_X + 88, preview_y, f"{current.defense}→?", COLOR_TEXT)
            return
        self._draw_change(CHOICE_X + 20, preview_y, current.atk, preview.atk)
        self._draw_change(CHOICE_X + 88, preview_y, current.defense, preview.defense)

    @staticmethod
    def _draw_change(x: int, y: int, before: int, after: int) -> None:
        color = COLOR_UP if after > before else COLOR_DOWN if after < before else COLOR_TEXT
        font.draw_text(x, y, f"{before}→{after}", color)
