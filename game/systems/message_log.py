"""ゲーム内ログの保持。仕様書 14章。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections import deque

LOG_CAPACITY = 100

# アイテム名などを黄色で強調するための目印（描画時に取り除く）
HIGHLIGHT_START = "\x01"
HIGHLIGHT_END = "\x02"


def highlight(text: str) -> str:
    return f"{HIGHLIGHT_START}{text}{HIGHLIGHT_END}"


def strip_markup(text: str) -> str:
    return text.replace(HIGHLIGHT_START, "").replace(HIGHLIGHT_END, "")


class MessageLog:
    def __init__(self, capacity: int = LOG_CAPACITY) -> None:
        self.capacity = capacity
        self._entries: deque[str] = deque(maxlen=capacity)

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> list[str]:
        """古い順のログ。"""
        return list(self._entries)

    def add(self, text: str) -> None:
        self._entries.append(text)

    def latest(self, count: int) -> list[str]:
        """新しいほうから count 件を、古い順に並べて返す。"""
        if count <= 0:
            return []
        return list(self._entries)[-count:]
