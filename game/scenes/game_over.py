"""ゲームオーバー画面。仕様書 6.6。

所持品・装備・レベル・所持金を失って拠点に戻る（引き継ぎは systems/meta.py）。
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
        to_camp: Callable[[], Scene],
    ) -> None:
        self.player_name = player_name
        self.floor_number = floor_number
        self.turn = turn
        self.controls = controls
        self.to_camp = to_camp
        self.frames = 0

    def update(self) -> Scene | None:
        self.frames += 1
        if self.frames >= INPUT_DELAY_FRAMES and self.controls.triggered("confirm"):
            return self.to_camp()
        return None

    def draw(self) -> None:
        pyxel.cls(0)
        font.draw_text_centered(56, f"{self.player_name}は力尽きた……", COLOR_TITLE)
        font.draw_text_centered(76, f"B{self.floor_number}F  {self.turn}ターン", COLOR_TEXT)
        font.draw_text_centered(96, "所持品と所持金は失われた。", COLOR_HINT)
        if self.frames >= INPUT_DELAY_FRAMES:
            font.draw_text_centered(124, "Enter: 拠点に戻る", COLOR_HINT)
