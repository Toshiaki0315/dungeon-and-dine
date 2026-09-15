"""ゲームオーバー画面。仕様書 6.6。

フェーズ2では、決定キーで新しい挑戦を始める。拠点へ戻る流れはフェーズ6で実装する。
"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.scenes import Scene
from game.ui import font
from game.ui.input import Controls

COLOR_TITLE = 8
COLOR_TEXT = 7
COLOR_HINT = 13
INPUT_DELAY_FRAMES = config.FPS  # 直前の操作で誤って閉じないよう、1秒は入力を受け付けない


class GameOverScene:
    def __init__(
        self,
        *,
        player_name: str,
        floor_number: int,
        turn: int,
        controls: Controls,
        new_run: Callable[[], Scene],
    ) -> None:
        self.player_name = player_name
        self.floor_number = floor_number
        self.turn = turn
        self.controls = controls
        self.new_run = new_run
        self.frames = 0

    def update(self) -> Scene | None:
        self.frames += 1
        if self.frames >= INPUT_DELAY_FRAMES and self.controls.triggered("confirm"):
            return self.new_run()
        return None

    def draw(self) -> None:
        pyxel.cls(0)
        font.draw_text_centered(64, f"{self.player_name}は力尽きた……", COLOR_TITLE)
        font.draw_text_centered(84, f"B{self.floor_number}F  {self.turn}ターン", COLOR_TEXT)
        if self.frames >= INPUT_DELAY_FRAMES:
            font.draw_text_centered(120, "Enter: もう一度挑戦する", COLOR_HINT)
