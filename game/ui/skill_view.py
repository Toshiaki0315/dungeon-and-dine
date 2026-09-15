"""スキル一覧。仕様書 6.8 / 14章。"""

from __future__ import annotations

import pyxel

from game import config
from game.systems.skills import SkillDef
from game.ui import font
from game.ui.input import Controls
from game.ui.log import wrap_text
from game.ui.menu import draw_window

COLOR_TEXT = 7
COLOR_DISABLED = 13  # MP が足りないスキルは灰色
COLOR_SUBTEXT = 13
COLOR_LINE = 5
COLOR_CURSOR = 5

X, Y, W, H = 24, config.MAP_TOP + 2, 272, 116


class SkillView:
    def __init__(self) -> None:
        self.skills: list[SkillDef] = []
        self.cursor = 0

    def open(self, skills: list[SkillDef]) -> None:
        self.skills = skills
        self.cursor = max(0, min(self.cursor, len(skills) - 1))

    def update(self, controls: Controls) -> str | bool | None:
        """選んだスキルの ID、閉じるなら True、それ以外は None を返す。"""
        if controls.triggered("cancel") or controls.triggered("skills"):
            return True
        if not self.skills:
            return None
        if controls.triggered_repeat("up"):
            self.cursor = (self.cursor - 1) % len(self.skills)
        elif controls.triggered_repeat("down"):
            self.cursor = (self.cursor + 1) % len(self.skills)
        elif controls.triggered("confirm"):
            return self.skills[self.cursor].id
        return None

    def draw(self, mp: int) -> None:
        draw_window(X, Y, W, H)
        font.draw_text(X + 8, Y + 5, "スキル", COLOR_TEXT)
        mp_text = f"MP {mp}"
        font.draw_text(X + W - 8 - font.text_width(mp_text), Y + 5, mp_text, COLOR_TEXT)
        pyxel.line(X + 4, Y + 15, X + W - 5, Y + 15, COLOR_LINE)

        for i, skill in enumerate(self.skills):
            row_y = Y + 19 + i * config.LINE_HEIGHT
            if i == self.cursor:
                pyxel.rect(X + 4, row_y - 1, W - 8, config.LINE_HEIGHT, COLOR_CURSOR)
            color = COLOR_TEXT if mp >= skill.mp else COLOR_DISABLED
            font.draw_text(X + 8, row_y, skill.name, color)
            cost = f"MP{skill.mp}"
            font.draw_text(X + W - 8 - font.text_width(cost), row_y, cost, color)

        if self.skills:
            description = self.skills[self.cursor].description
            lines = wrap_text(description, W - 16, font.text_width)[:2]
            pyxel.line(X + 4, Y + H - 36, X + W - 5, Y + H - 36, COLOR_LINE)
            for i, line in enumerate(lines):
                font.draw_text(X + 8, Y + H - 32 + i * config.LINE_HEIGHT, line, COLOR_SUBTEXT)
        font.draw_text(X + 8, Y + H - 11, "決定: 使う  K / Esc: 閉じる", COLOR_SUBTEXT)
