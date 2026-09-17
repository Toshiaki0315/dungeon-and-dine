"""ログ2行とログ履歴。仕様書 2.3 / 14章。

アイテム名などは systems/message_log.py の highlight() で囲まれており、黄色で描く。
"""

from __future__ import annotations

from collections.abc import Callable

from game import config
from game.systems.message_log import HIGHLIGHT_END, HIGHLIGHT_START, MessageLog, strip_markup
from game.ui import font
from game.ui.input import Controls

COLOR_TEXT = 7
COLOR_OLD = 13
COLOR_HINT = 13
COLOR_HIGHLIGHT = 10  # 黄色

RECENT_LINES = 2
HISTORY_LINES = 20
TEXT_WIDTH = config.SCREEN_WIDTH - 16

WrappedLine = tuple[str, bool]  # (行, 行頭で強調中か)


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


def split_markup(line: str, highlighted: bool) -> tuple[list[tuple[str, bool]], bool]:
    """強調の目印で行を区切り、(文字列, 強調するか) の並びと、行末での強調状態を返す。"""
    segments: list[tuple[str, bool]] = []
    current = ""
    for char in line:
        if char in (HIGHLIGHT_START, HIGHLIGHT_END):
            if current:
                segments.append((current, highlighted))
                current = ""
            highlighted = char == HIGHLIGHT_START
        else:
            current += char
    if current:
        segments.append((current, highlighted))
    return segments, highlighted


def wrap_entry(entry: str, max_width: int = TEXT_WIDTH) -> list[WrappedLine]:
    lines = wrap_text(entry, max_width, lambda s: font.text_width(strip_markup(s)))
    result: list[WrappedLine] = []
    highlighted = False
    for line in lines:
        result.append((line, highlighted))
        _, highlighted = split_markup(line, highlighted)
    return result


def draw_markup_line(x: int, y: int, line: WrappedLine, color: int) -> None:
    text, highlighted = line
    segments, _ = split_markup(text, highlighted)
    for segment, is_highlight in segments:
        font.draw_text(x, y, segment, COLOR_HIGHLIGHT if is_highlight else color)
        x += font.text_width(segment)


def _wrapped(entries: list[str]) -> list[WrappedLine]:
    return [line for entry in entries for line in wrap_entry(entry)]


def draw_recent(log: MessageLog, y: int) -> None:
    """最新のログを2行ぶん描く（折り返した行も1行と数える）。"""
    lines = _wrapped(log.latest(RECENT_LINES))[-RECENT_LINES:]
    for i, line in enumerate(lines):
        color = COLOR_TEXT if i == len(lines) - 1 else COLOR_OLD
        draw_markup_line(8, y + i * config.LINE_HEIGHT, line, color)


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
        font.draw_text(8, 6, f"ログ履歴  {len(self.log)}/{self.log.capacity}", COLOR_TEXT)
        lines = _wrapped(self.log.entries)
        end = len(lines) - self.scroll
        for i, line in enumerate(lines[max(0, end - HISTORY_LINES) : end]):
            draw_markup_line(8, 32 + i * config.LINE_HEIGHT, line, COLOR_TEXT)
        hint = "↑↓: スクロール  L / Esc: 閉じる"
        font.draw_text(8, config.SCREEN_HEIGHT - 22, hint, COLOR_HINT)
