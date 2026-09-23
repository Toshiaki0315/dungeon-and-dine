"""ベースキャンプ（拠点）画面。仕様書 12.3。

左にメニュー、右に拠点の様子と記録を表示する。施設を選ぶと一覧画面になる。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

from game import config
from game.entities.item import ItemDef, ItemInstance
from game.scenes import Scene
from game.systems import meta as meta_system
from game.systems.catalog import Catalog
from game.systems.meta import BaseCampParams, MetaProgress
from game.ui import font
from game.ui.input import Controls
from game.ui.menu import draw_window
from game.ui.notebook_view import NotebookView
from game.ui.sprites import SpriteSheet

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_CURSOR = 5
COLOR_LINE = 5
COLOR_TITLE = 10
COLOR_DISABLED = 13
COLOR_WARN = 8  # 拠点の枠を超えているときの色

MENU_X, MENU_Y, MENU_W, MENU_H = 16, 48, 192, 232
PANEL_X, PANEL_W = 224, 400
# 10行並べたうえでメッセージを出しても最後の行と重ならない高さにする
LIST_X, LIST_Y, LIST_W, LIST_H = 16, 44, 608, 300
ROWS = 10

FACILITIES: tuple[tuple[str, str], ...] = (
    ("depart", "出発"),
    ("shop", "道具屋"),
    ("appraise", "鑑定屋"),
    ("uncurse", "解呪屋"),
    ("storage", "倉庫"),
    ("expand", "拡張"),
    ("notebook", "レシピ手帳"),
)


class Mode(Enum):
    MENU = auto()
    LIST = auto()  # 道具屋・鑑定屋・解呪屋・倉庫・拡張
    NOTEBOOK = auto()


@dataclass(frozen=True)
class Entry:
    """一覧の1行。payload は施設ごとの対象（アイテムの定義・個体・拡張の種類）。"""

    label: str
    payload: object
    detail: str = ""


class BaseCampScene:
    def __init__(
        self,
        *,
        controls: Controls,
        sprites: SpriteSheet,
        meta: MetaProgress,
        params: BaseCampParams,
        catalog: Catalog,
        depart: Callable[[], Scene],
        save_meta: Callable[[], None],
        message: str = "",
    ) -> None:
        self.controls = controls
        self.sprites = sprites
        self.meta = meta
        self.params = params
        self.catalog = catalog
        self.depart = depart
        self.save_meta = save_meta
        self.message = message
        self.mode = Mode.MENU
        self.cursor = 0
        self.facility = ""
        self.list_cursor = 0
        self.list_scroll = 0
        self.column = 0  # 倉庫: 0 = 持ち物、1 = 倉庫
        self.notebook_view = NotebookView(catalog, meta.notebook)

    # --- 更新 ---

    def update(self) -> Scene | None:
        if self.mode == Mode.NOTEBOOK:
            if self.notebook_view.update(self.controls):
                self.mode = Mode.MENU
            return None
        if self.mode == Mode.LIST:
            self._update_list()
            return None
        return self._update_menu()

    def _update_menu(self) -> Scene | None:
        c = self.controls
        if c.triggered_repeat("up"):
            self.cursor = (self.cursor - 1) % len(FACILITIES)
        elif c.triggered_repeat("down"):
            self.cursor = (self.cursor + 1) % len(FACILITIES)
        elif c.triggered("confirm"):
            facility = FACILITIES[self.cursor][0]
            if facility == "depart":
                return self.depart()
            if facility == "notebook":
                self.notebook_view.open()
                self.mode = Mode.NOTEBOOK
                return None
            self.facility = facility
            self.list_cursor = 0
            self.list_scroll = 0
            self.column = 0
            self.message = ""
            self.mode = Mode.LIST
        return None

    def _update_list(self) -> None:
        c = self.controls
        if c.triggered("cancel"):
            self.mode = Mode.MENU
            self.message = ""
            return
        entries = self._entries()
        if self.facility == "storage" and (
            c.triggered_repeat("left") or c.triggered_repeat("right")
        ):
            self.column = 1 - self.column
            self.list_cursor = 0
            self.list_scroll = 0
            return
        if entries:
            if c.triggered_repeat("up"):
                self.list_cursor = (self.list_cursor - 1) % len(entries)
            elif c.triggered_repeat("down"):
                self.list_cursor = (self.list_cursor + 1) % len(entries)
            elif c.triggered("confirm"):
                self.message = self._apply(entries[self.list_cursor])
                self.save_meta()
        self._clamp(len(entries))

    def _apply(self, entry: Entry) -> str:
        meta, params = self.meta, self.params
        payload = entry.payload
        if self.facility == "shop" and isinstance(payload, ItemDef):
            return meta_system.buy(meta, params, payload)
        if self.facility == "appraise" and isinstance(payload, ItemInstance):
            return meta_system.appraise(meta, params, payload)
        if self.facility == "uncurse" and isinstance(payload, ItemInstance):
            return meta_system.uncurse(meta, params, payload)
        if self.facility == "storage" and isinstance(payload, ItemInstance):
            if self.column == 0:
                return meta_system.deposit(meta, payload)
            return meta_system.withdraw(meta, payload)
        if self.facility == "expand":
            if payload == "inventory":
                return meta_system.expand_inventory(meta, params)
            return meta_system.expand_storage(meta, params)
        return ""

    def _entries(self) -> list[Entry]:
        meta, params = self.meta, self.params
        if self.facility == "shop":
            items = sorted(meta_system.shop_items(self.catalog.items), key=lambda i: i.price or 0)
            bundles = params.bundles
            return [
                Entry(
                    f"{i.name}" + (f"（{bundles[i.id]}本）" if i.id in bundles else ""),
                    i,
                    f"{i.price}G",
                )
                for i in items
            ]
        if self.facility == "appraise":
            return [
                Entry(item.name, item, f"{params.appraise_cost}G")
                for item in meta.loadout.items.items
                if item.is_equipment and not item.identified
            ]
        if self.facility == "uncurse":
            return [
                Entry(item.name, item, f"{params.uncurse_cost}G")
                for item in meta.loadout.items.items
                if item.is_equipment
            ]
        if self.facility == "storage":
            source = meta.loadout.items if self.column == 0 else meta.storage
            return [Entry(item.name, item) for item in source.items]
        if self.facility == "expand":
            inventory, storage = params.inventory_expansion, params.storage_expansion
            return [
                Entry(
                    f"持ち物の枠 +{inventory.amount}",
                    "inventory",
                    f"{inventory.cost}G  残り{inventory.max_times - meta.inventory_expansions}回",
                ),
                Entry(
                    f"倉庫の枠 +{storage.amount}",
                    "storage",
                    f"{storage.cost}G  残り{storage.max_times - meta.storage_expansions}回",
                ),
            ]
        return []

    def _clamp(self, count: int) -> None:
        self.list_cursor = max(0, min(self.list_cursor, count - 1))
        if self.list_cursor < self.list_scroll:
            self.list_scroll = self.list_cursor
        elif self.list_cursor >= self.list_scroll + ROWS:
            self.list_scroll = self.list_cursor - ROWS + 1
        self.list_scroll = max(0, min(self.list_scroll, max(0, count - ROWS)))

    # --- 描画 ---

    def draw(self) -> None:
        pyxel.cls(0)
        font.draw_text(16, 12, "ベースキャンプ", COLOR_TITLE)
        funds = f"拠点資金 {self.meta.funds}G"
        font.draw_text(config.SCREEN_WIDTH - 16 - font.text_width(funds), 12, funds, COLOR_TEXT)
        if self.mode == Mode.NOTEBOOK:
            self.notebook_view.draw()
            return
        if self.mode == Mode.LIST:
            self._draw_list()
            return
        self._draw_menu()

    def _draw_menu(self) -> None:
        draw_window(MENU_X, MENU_Y, MENU_W, MENU_H)
        for i, (_, label) in enumerate(FACILITIES):
            y = MENU_Y + 12 + i * config.LINE_HEIGHT * 3 // 2
            if i == self.cursor:
                pyxel.rect(MENU_X + 8, y - 2, MENU_W - 16, config.LINE_HEIGHT, COLOR_CURSOR)
            font.draw_text(MENU_X + 16, y, label, COLOR_TEXT)

        draw_window(PANEL_X, MENU_Y, PANEL_W, MENU_H)
        frame = pyxel.frame_count // 5
        self.sprites.draw_scaled("campfire", PANEL_X + 152, MENU_Y + 32, 5, frame)
        # 背負い袋で広げた枠のまま持ち帰ると、拠点の枠より多く持っていることがある（仕様書 11.1）
        items = self.meta.loadout.items
        over = len(items) - items.capacity
        lines = [
            (f"持ち物 {len(items)}/{items.capacity}", COLOR_WARN if over > 0 else COLOR_SUBTEXT),
            (f"倉庫 {len(self.meta.storage)}/{self.meta.storage.capacity}", COLOR_SUBTEXT),
            (f"最深到達 B{self.meta.deepest_floor}F　クリア {self.meta.clears}回", COLOR_SUBTEXT),
            (
                f"レシピ {len(self.meta.notebook.discovered)}/{len(self.catalog.recipes)}",
                COLOR_SUBTEXT,
            ),
        ]
        if over > 0:
            lines.append((f"枠を{over}超えている。倉庫に預けよう。", COLOR_WARN))
        for i, (line, color) in enumerate(lines):
            font.draw_text(PANEL_X + 20, MENU_Y + 132 + i * config.LINE_HEIGHT, line, color)
        if self.message:
            font.draw_text(MENU_X, config.SCREEN_HEIGHT - 24, self.message, COLOR_TEXT)

    def _draw_list(self) -> None:
        label = dict(FACILITIES)[self.facility]
        draw_window(LIST_X, LIST_Y, LIST_W, LIST_H)
        title = label if self.facility != "storage" else f"{label}（{self._column_label()}）"
        font.draw_text(LIST_X + 16, LIST_Y + 10, title, COLOR_TEXT)
        rows = self._entries()
        if len(rows) > ROWS:  # 1画面に収まらないときは、いま何番目かを出す
            count = f"{self.list_cursor + 1}/{len(rows)}"
            font.draw_text(
                LIST_X + LIST_W - 16 - font.text_width(count), LIST_Y + 10, count, COLOR_SUBTEXT
            )
        pyxel.line(LIST_X + 8, LIST_Y + 30, LIST_X + LIST_W - 10, LIST_Y + 30, COLOR_LINE)

        entries = self._entries()
        if not entries:
            font.draw_text(LIST_X + 16, LIST_Y + 40, "何もない。", COLOR_SUBTEXT)
        for row, entry in enumerate(entries[self.list_scroll : self.list_scroll + ROWS]):
            index = self.list_scroll + row
            y = LIST_Y + 38 + row * config.LINE_HEIGHT
            if index == self.list_cursor:
                pyxel.rect(LIST_X + 8, y - 2, LIST_W - 16, config.LINE_HEIGHT, COLOR_CURSOR)
            font.draw_text(LIST_X + 16, y, entry.label, COLOR_TEXT)
            if entry.detail:
                x = LIST_X + LIST_W - 16 - font.text_width(entry.detail)
                font.draw_text(x, y, entry.detail, COLOR_SUBTEXT)
        if self.message:
            font.draw_text(LIST_X + 16, LIST_Y + LIST_H - 44, self.message, COLOR_TEXT)
        hint = "決定: 選ぶ  Esc: 戻る"
        if self.facility == "storage":
            hint = "決定: 預ける／引き出す  ←→: 切り替え  Esc: 戻る"
        font.draw_text(LIST_X + 16, LIST_Y + LIST_H - 22, hint, COLOR_SUBTEXT)

    def _column_label(self) -> str:
        return "持ち物 → 倉庫" if self.column == 0 else "倉庫 → 持ち物"
