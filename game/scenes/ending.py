"""エンディング画面。仕様書 4章 / 8.3。

エンディングの階（B100F）のボスを倒したときに表示する。
迷宮に最下層はないので、見たあとは「さらに潜る」か「拠点へ帰還する」かを選ぶ。
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
COLOR_CURSOR = 5

INPUT_DELAY_FRAMES = config.FPS
STAR_COUNT = 24

CHOICE_DIVE = "dive"
CHOICE_RETURN = "return"
CHOICES: tuple[tuple[str, str], ...] = (
    ("さらに潜る", CHOICE_DIVE),
    ("拠点へ帰還する", CHOICE_RETURN),
)
CHOICE_Y = 304


class EndingScene:
    def __init__(
        self,
        *,
        player_name: str,
        boss_name: str,
        floor_number: int,
        turn: int,
        level: int,
        clears: int,
        controls: Controls,
        sprites: SpriteSheet,
        to_camp: Callable[[], Scene],
        to_dungeon: Callable[[], Scene],
    ) -> None:
        self.player_name = player_name
        self.boss_name = boss_name
        self.floor_number = floor_number
        self.turn = turn
        self.level = level
        self.clears = clears
        self.controls = controls
        self.sprites = sprites
        self.to_camp = to_camp
        self.to_dungeon = to_dungeon
        self.frames = 0
        self.index = 0

    def update(self) -> Scene | None:
        self.frames += 1
        if self.frames < INPUT_DELAY_FRAMES:
            return None
        c = self.controls
        step = int(c.triggered_repeat("down")) - int(c.triggered_repeat("up"))
        if step:
            self.index = (self.index + step) % len(CHOICES)
        if c.triggered("confirm"):
            if CHOICES[self.index][1] == CHOICE_DIVE:
                return self.to_dungeon()
            return self.to_camp()
        return None

    def draw(self) -> None:
        pyxel.cls(0)
        for i in range(STAR_COUNT):
            # 舞い上がる光の粒（迷宮から抜け出す演出）
            x = (i * 37 + 11) % config.SCREEN_WIDTH
            y = config.SCREEN_HEIGHT - (pyxel.frame_count // 2 + i * 13) % config.SCREEN_HEIGHT
            pyxel.rect(x, y, 2, 2, COLOR_STAR if i % 3 else COLOR_TITLE)

        font.draw_text_centered(120, f"{self.boss_name}を討ち果たした！", COLOR_TITLE)
        reached = f"{self.player_name}は B{self.floor_number}F へ到達した。"
        font.draw_text_centered(160, reached, COLOR_TEXT)
        font.draw_text_centered(192, f"Lv{self.level}　{self.turn}ターン", COLOR_TEXT)
        font.draw_text_centered(220, f"クリア {self.clears}回", COLOR_HINT)
        frame = pyxel.frame_count // 5
        # 焚き火は選択肢の上に収める（大きすぎると下の行と重なる）
        self.sprites.draw_scaled("campfire", config.SCREEN_WIDTH // 2 - 16, 240, 4, frame)

        if self.frames < INPUT_DELAY_FRAMES:
            return
        font.draw_text_centered(CHOICE_Y - 24, "迷宮に果てはない。どうする？", COLOR_HINT)
        for i, (label, _) in enumerate(CHOICES):
            y = CHOICE_Y + i * (config.LINE_HEIGHT + 8)
            width = font.text_width(label)
            x = (config.SCREEN_WIDTH - width) // 2
            if i == self.index:
                pyxel.rect(x - 8, y - 2, width + 16, config.LINE_HEIGHT, COLOR_CURSOR)
            font.draw_text(x, y, label, COLOR_TEXT)
