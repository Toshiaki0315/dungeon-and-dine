"""エンディング画面。仕様書 4章 / 8.3。

B20F のボスを倒したときに表示する。決定キーで拠点へ戻る。
"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.scenes import Scene
from game.ui import font
from game.ui.input import Controls
from game.ui.sprites import SpriteSheet

COLOR_TITLE = 10
COLOR_TEXT = 7
COLOR_HINT = 13
COLOR_STAR = 7

INPUT_DELAY_FRAMES = config.FPS
STAR_COUNT = 24


class EndingScene:
    def __init__(
        self,
        *,
        player_name: str,
        turn: int,
        level: int,
        clears: int,
        controls: Controls,
        sprites: SpriteSheet,
        to_camp: Callable[[], Scene],
    ) -> None:
        self.player_name = player_name
        self.turn = turn
        self.level = level
        self.clears = clears
        self.controls = controls
        self.sprites = sprites
        self.to_camp = to_camp
        self.frames = 0

    def update(self) -> Scene | None:
        self.frames += 1
        if self.frames >= INPUT_DELAY_FRAMES and self.controls.triggered("confirm"):
            return self.to_camp()
        return None

    def draw(self) -> None:
        pyxel.cls(0)
        for i in range(STAR_COUNT):
            # 舞い上がる光の粒（迷宮から抜け出す演出）
            x = (i * 37 + 11) % config.SCREEN_WIDTH
            y = config.SCREEN_HEIGHT - (pyxel.frame_count // 2 + i * 13) % config.SCREEN_HEIGHT
            pyxel.pset(x, y, COLOR_STAR if i % 3 else COLOR_TITLE)

        font.draw_text_centered(36, "奈落の大喰らいを討ち果たした！", COLOR_TITLE)
        font.draw_text_centered(60, f"{self.player_name}は迷宮を踏破した。", COLOR_TEXT)
        font.draw_text_centered(80, f"Lv{self.level}　{self.turn}ターン", COLOR_TEXT)
        font.draw_text_centered(100, f"クリア {self.clears}回", COLOR_HINT)
        frame = pyxel.frame_count // 5
        self.sprites.draw_scaled("campfire", config.SCREEN_WIDTH // 2 - 20, 112, 5, frame)
        if self.frames >= INPUT_DELAY_FRAMES:
            font.draw_text_centered(config.SCREEN_HEIGHT - 14, "Enter: 拠点に戻る", COLOR_HINT)
