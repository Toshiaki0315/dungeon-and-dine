"""インベントリ画面。仕様書 14章。

フェーズ2では枠と使用枠数だけを表示する。アイテム一覧はフェーズ3で実装する。
"""

from __future__ import annotations

import pyxel

from game import config
from game.ui import font
from game.ui.menu import draw_window

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_LINE = 5


def draw_inventory(item_count: int, capacity: int) -> None:
    x, y, w, h = 60, config.MAP_TOP + 10, 200, 100
    draw_window(x, y, w, h)
    font.draw_text(x + 8, y + 6, "道具", COLOR_TEXT)
    count = f"{item_count}/{capacity}"
    font.draw_text(x + w - 8 - font.text_width(count), y + 6, count, COLOR_TEXT)
    pyxel.line(x + 4, y + 17, x + w - 5, y + 17, COLOR_LINE)
    if item_count == 0:
        font.draw_text(x + 8, y + 24, "何も持っていない。", COLOR_SUBTEXT)
    font.draw_text(x + 8, y + h - 12, "I / Esc: 閉じる", COLOR_SUBTEXT)
