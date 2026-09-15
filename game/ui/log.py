"""ログ2行とログ履歴。仕様書 2.3 / 14章。"""

from __future__ import annotations

from collections.abc import Callable

from game import config
from game.systems.message_log import MessageLog
from game.ui import font
from game.ui.input import Controls

COLOR_TEXT = 7
COLOR_OLD = 13
COLOR_HINT = 13

RECENT_LINES = 2
HISTORY_LINES = 14
TEXT_WIDTH = config.SCREEN_WIDTH - 8


def wrap_text(text: str, max_width: int, measure: Callable[[str], int]) -> list[str]:
    """描画幅が max_width を超えないように、文字単位で折り返す。"""
    lines: list[str] = []
    current = ""
    for char in text:
        if current and measure(current + char) > max_width:
            lines.append(current)
            current = char
        else:
            current += char
    lines.append(current)
    return lines


def _wrapped(entries: list[str]) -> list[str]:
    return [line for entry in entries for line in wrap_text(entry, TEXT_WIDTH, font.text_width)]


def draw_recent(log: MessageLog, y: int) -> None:
    """最新のログを2行ぶん描く（折り返した行も1行と数える）。"""
    lines = _wrapped(log.latest(RECENT_LINES))[-RECENT_LINES:]
    for i, line in enumerate(lines):
        color = COLOR_TEXT if i == len(lines) - 1 else COLOR_OLD
        font.draw_text(4, y + i * config.LINE_HEIGHT, line, color)


class LogHistoryView:
    def __init__(self, log: MessageLog) -> None:
        self.log = log
        self.scroll = 0  # 最新からさかのぼった行数

    def open(self) -> None:
        self.scroll = 0

    def update(self, controls: Controls) -> bool:
        """閉じたら True を返す。"""
        if controls.triggered("cancel") or controls.triggered("log_history"):
            return True
        max_scroll = max(0, len(_wrapped(self.log.entries)) - HISTORY_LINES)
        if controls.triggered_repeat("up"):
            self.scroll = min(max_scroll, self.scroll + 1)
        elif controls.triggered_repeat("down"):
            self.scroll = max(0, self.scroll - 1)
        return False

    def draw(self) -> None:
        font.draw_text(4, 3, f"ログ履歴  {len(self.log)}/{self.log.capacity}", COLOR_TEXT)
        lines = _wrapped(self.log.entries)
        end = len(lines) - self.scroll
        for i, line in enumerate(lines[max(0, end - HISTORY_LINES) : end]):
            font.draw_text(4, 16 + i * config.LINE_HEIGHT, line, COLOR_TEXT)
        hint = "↑↓: スクロール  L / Esc: 閉じる"
        font.draw_text(4, config.SCREEN_HEIGHT - 11, hint, COLOR_HINT)
