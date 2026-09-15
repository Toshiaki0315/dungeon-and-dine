"""コマンドバー。仕様書 3.1。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pyxel

from game import config
from game.ui import font

COLOR_TEXT = 7
COLOR_DISABLED = 13  # 選べないコマンドは灰色
COLOR_FRAME = 1
COLOR_FOCUS_BG = 5


@dataclass(frozen=True)
class CommandDef:
    id: str
    label: str


COMMANDS: tuple[CommandDef, ...] = (
    CommandDef("attack", "攻撃"),
    CommandDef("items", "道具"),
    CommandDef("skills", "スキル"),
    CommandDef("cook", "料理"),
    CommandDef("equipment", "装備"),
    CommandDef("map", "地図"),
)

BAR_Y = config.MAP_TOP + config.MAP_VIEW_HEIGHT + 2
BUTTON_H = 11
BUTTON_W = config.SCREEN_WIDTH // len(COMMANDS)


def button_rect(index: int) -> tuple[int, int, int, int]:
    """ボタンの (x, y, w, h)。"""
    return (index * BUTTON_W + 1, BAR_Y, BUTTON_W - 2, BUTTON_H)


def hit_test(px: int, py: int) -> int | None:
    """画面座標にあるボタンの番号。ボタンの外なら None。"""
    for index in range(len(COMMANDS)):
        x, y, w, h = button_rect(index)
        if x <= px < x + w and y <= py < y + h:
            return index
    return None


def command_label(command_id: str) -> str:
    return next(c.label for c in COMMANDS if c.id == command_id)


class CommandBar:
    def __init__(self) -> None:
        self.index = 0

    @property
    def selected(self) -> CommandDef:
        return COMMANDS[self.index]

    def move(self, delta: int) -> None:
        self.index = (self.index + delta) % len(COMMANDS)

    def draw(self, *, focused: bool, is_enabled: Callable[[str], bool]) -> None:
        for index, command in enumerate(COMMANDS):
            x, y, w, h = button_rect(index)
            if focused and index == self.index:
                pyxel.rect(x, y, w, h, COLOR_FOCUS_BG)
            else:
                pyxel.rectb(x, y, w, h, COLOR_FRAME)
            color = COLOR_TEXT if is_enabled(command.id) else COLOR_DISABLED
            text_x = x + (w - font.text_width(command.label)) // 2
            font.draw_text(text_x, y + 2, command.label, color)
