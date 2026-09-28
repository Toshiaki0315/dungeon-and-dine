"""ゲームオーバー画面。仕様書 6.6。

所持品・装備・レベル・所持金を失って拠点に戻る（引き継ぎは systems/meta.py）。
"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.scenes import Scene
from game.systems.meta import MetaProgress, ScoreEntry
from game.ui import font
from game.ui.input import Controls
from game.ui.ranking_view import RankingView

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
        meta: MetaProgress | None = None,
        latest: ScoreEntry | None = None,
    ) -> None:
        self.player_name = player_name
        self.floor_number = floor_number
        self.turn = turn
        self.controls = controls
        self.to_camp = to_camp
        self.frames = 0
        self.ranking = RankingView(meta, latest) if meta is not None else None

    def update(self) -> Scene | None:
        self.frames += 1
        used_click = self.ranking.update(self.controls) if self.ranking is not None else False
        if self.frames < INPUT_DELAY_FRAMES:
            return None
        if self.controls.triggered("confirm") or self.controls.right_clicked():
            return self.to_camp()
        if not used_click and self.controls.clicked() is not None:
            return self.to_camp()  # タブ以外をクリックしたら閉じる
        return None

    def draw(self) -> None:
        pyxel.cls(0)
        font.draw_text_centered(12, f"{self.player_name}は力尽きた……", COLOR_TITLE)
        summary = f"B{self.floor_number}F  {self.turn}ターン  所持品と所持金は失われた。"
        font.draw_text_centered(36, summary, COLOR_HINT)
        if self.ranking is not None:
            self.ranking.draw(16, 64, config.SCREEN_WIDTH - 32, 264)
        if self.frames >= INPUT_DELAY_FRAMES:
            hint = "Enter / クリック: 拠点に戻る"
            font.draw_text_centered(config.SCREEN_HEIGHT - 24, hint, COLOR_HINT)
