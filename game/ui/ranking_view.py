"""ランキング画面。仕様書 6.6。

これまでの挑戦を「到達した階層」と「獲得した所持金」の2種類で並べる（左右キーで切り替える）。
"""

from __future__ import annotations

import pyxel

from game import config
from game.systems.meta import (
    RANKING_SIZE,
    MetaProgress,
    ScoreEntry,
    ranking_by_floor,
    ranking_by_gold,
)
from game.ui import font
from game.ui.input import Controls
from game.ui.menu import draw_window

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_LINE = 5
COLOR_TAB = 5
COLOR_LATEST = 10  # 今回の記録
COLOR_CLEAR = 11  # クリアした挑戦

TABS = ("到達した階層", "獲得した所持金")


class RankingView:
    def __init__(self, meta: MetaProgress, latest: ScoreEntry | None = None) -> None:
        self.meta = meta
        self.latest = latest  # 今回の挑戦（一覧の中で色を変えて示す）
        self.tab = 0

    def update(self, controls: Controls) -> None:
        if controls.triggered_repeat("left") or controls.triggered_repeat("right"):
            self.tab = 1 - self.tab

    def entries(self) -> list[ScoreEntry]:
        scores = self.meta.scores
        if self.tab == 0:
            return ranking_by_floor(scores, RANKING_SIZE)
        return ranking_by_gold(scores, RANKING_SIZE)

    def draw(self, x: int, y: int, w: int, h: int) -> None:
        draw_window(x, y, w, h)
        for i, label in enumerate(TABS):
            tab_x = x + 8 + i * 116
            if i == self.tab:
                pyxel.rect(tab_x - 4, y + 4, font.text_width(label) + 8, 10, COLOR_TAB)
            font.draw_text(tab_x, y + 5, label, COLOR_TEXT)
        hint = "←→: 切り替え"
        font.draw_text(x + w - 8 - font.text_width(hint), y + 5, hint, COLOR_SUBTEXT)
        pyxel.line(x + 4, y + 15, x + w - 5, y + 15, COLOR_LINE)

        entries = self.entries()
        if not entries:
            font.draw_text(x + 8, y + 20, "まだ記録がない。", COLOR_SUBTEXT)
            return
        for rank, entry in enumerate(entries, start=1):
            row_y = y + 19 + (rank - 1) * config.LINE_HEIGHT
            color = COLOR_TEXT
            if entry is self.latest:
                color = COLOR_LATEST  # 今回の記録
            elif entry.outcome == "clear":
                color = COLOR_CLEAR
            font.draw_text(x + 8, row_y, f"{rank:>2}", COLOR_SUBTEXT)
            font.draw_text(x + 24, row_y, entry.name, color)
            font.draw_text(x + 110, row_y, f"B{entry.floor}F", color)
            gold = f"{entry.gold}G"
            font.draw_text(x + 176 - font.text_width(gold), row_y, gold, color)
            font.draw_text(x + 190, row_y, f"{entry.turn}ターン", COLOR_SUBTEXT)
            font.draw_text(x + 250, row_y, entry.outcome_label, COLOR_SUBTEXT)
