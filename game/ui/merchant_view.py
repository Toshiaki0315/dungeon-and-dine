"""迷宮の行商人との対話画面。仕様書 12.4。

買う・解呪・解毒の3つを扱う。支払いは迷宮の中で拾った所持金（拠点資金ではない）。
"""

from __future__ import annotations

import pyxel

from game import config
from game.entities.item import ItemDef, ItemInstance
from game.systems import merchant
from game.systems.game_state import GameState
from game.ui import font
from game.ui.input import Controls
from game.ui.menu import draw_window

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_CURSOR = 5
COLOR_LINE = 5
COLOR_PRICE = 10
COLOR_POOR = 8  # 買えないものは赤

LIST_X, LIST_Y, LIST_W, LIST_H = 24, config.MAP_TOP + 2, 196, 116
ROWS = 8

MENU_BUY = "buy"
MENU_UNCURSE = "uncurse"
MENU_CURE = "cure"
MENU_LEAVE = "leave"
MENU: tuple[tuple[str, str], ...] = (
    ("買う", MENU_BUY),
    ("呪いを解く", MENU_UNCURSE),
    ("状態異常を治す", MENU_CURE),
    ("立ち去る", MENU_LEAVE),
)


class MerchantView:
    """行商人のメニュー。開いている間はターンが進まない。"""

    def __init__(self, state: GameState) -> None:
        self.state = state
        self.cursor = 0
        self.scroll = 0
        self.mode = "menu"  # "menu" / "buy" / "uncurse"
        self.message = ""

    def open(self) -> None:
        self.cursor = 0
        self.scroll = 0
        self.mode = "menu"
        self.message = "何か入り用かね。"

    # --- 一覧の中身 ---

    def stock(self) -> list[ItemDef]:
        return merchant.stock(self.state.catalog.items, self.state.params.spawn)

    def cursed_items(self) -> list[ItemInstance]:
        """呪われている可能性のある持ち物（装備中のものを含む）。"""
        return [i for i in self.state.inventory.items if i.cursed or not i.curse_known]

    def _rows(self) -> int:
        if self.mode == "buy":
            return len(self.stock())
        if self.mode == "uncurse":
            return len(self.cursed_items())
        return len(MENU)

    # --- 更新 ---

    def update(self, controls: Controls) -> bool:
        """閉じるなら True を返す。"""
        if controls.triggered("cancel"):
            if self.mode == "menu":
                return True
            self.mode = "menu"
            self.cursor = 0
            self.scroll = 0
            return False

        count = self._rows()
        if count:
            if controls.triggered_repeat("up"):
                self.cursor = (self.cursor - 1) % count
            elif controls.triggered_repeat("down"):
                self.cursor = (self.cursor + 1) % count
        if controls.triggered("confirm"):
            return self._confirm()
        self._clamp()
        return False

    def _confirm(self) -> bool:
        params = self.state.params.spawn
        player = self.state.player
        if self.mode == "menu":
            action = MENU[self.cursor][1]
            if action == MENU_LEAVE:
                return True
            if action == MENU_CURE:
                self.message = merchant.cure(player, self.state.catalog.statuses, params)
                return False
            self.mode = action
            self.cursor = 0
            self.scroll = 0
            return False
        if self.mode == "buy":
            items = self.stock()
            if items:
                definition = items[self.cursor]
                self.message = merchant.buy(player, self.state.inventory, definition, params)
            return False
        items = self.cursed_items()
        if items:
            self.message = merchant.uncurse(player, items[self.cursor], params)
            self.cursor = 0
        return False

    def _clamp(self) -> None:
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + ROWS:
            self.scroll = self.cursor - ROWS + 1

    # --- 描画 ---

    def draw(self) -> None:
        draw_window(LIST_X, LIST_Y, LIST_W, LIST_H)
        title = {"menu": "行商人", "buy": "買う", "uncurse": "呪いを解く"}[self.mode]
        font.draw_text(LIST_X + 8, LIST_Y + 5, title, COLOR_TEXT)
        gold = f"所持金 {self.state.player.gold}G"
        font.draw_text(LIST_X + LIST_W - 8 - font.text_width(gold), LIST_Y + 5, gold, COLOR_PRICE)
        pyxel.line(LIST_X + 4, LIST_Y + 15, LIST_X + LIST_W - 5, LIST_Y + 15, COLOR_LINE)

        if self.mode == "menu":
            self._draw_rows([label for label, _ in MENU], [""] * len(MENU))
        elif self.mode == "buy":
            items = self.stock()
            prices = [merchant.price_of(d, self.state.params.spawn) for d in items]
            labels = [d.name for d in items]
            self._draw_rows(labels, [f"{p}G" for p in prices], prices)
        else:
            items = self.cursed_items()
            cost = self.state.params.spawn.merchant_uncurse_cost
            labels = [i.name for i in items]
            self._draw_rows(labels, [f"{cost}G"] * len(items), [cost] * len(items))
            if not items:
                font.draw_text(LIST_X + 8, LIST_Y + 22, "呪われた持ち物はない。", COLOR_SUBTEXT)

        if self.message:
            font.draw_text(LIST_X + 8, LIST_Y + LIST_H - 14, self.message, COLOR_SUBTEXT)

    def _draw_rows(
        self, labels: list[str], suffixes: list[str], prices: list[int] | None = None
    ) -> None:
        for row, index in enumerate(range(self.scroll, min(len(labels), self.scroll + ROWS))):
            y = LIST_Y + 20 + row * config.LINE_HEIGHT
            if index == self.cursor:
                pyxel.rect(LIST_X + 4, y - 1, LIST_W - 8, config.LINE_HEIGHT, COLOR_CURSOR)
            font.draw_text(LIST_X + 12, y, labels[index], COLOR_TEXT)
            if suffixes[index]:
                affordable = prices is None or self.state.player.gold >= prices[index]
                color = COLOR_PRICE if affordable else COLOR_POOR
                x = LIST_X + LIST_W - 12 - font.text_width(suffixes[index])
                font.draw_text(x, y, suffixes[index], color)
