"""ダメージポップアップ・被弾の点滅・画面の揺れ・レベルアップの光。仕様書 14章。

座標はマップのタイル座標で受け取り、描画のときに画面座標へ変換する。
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

import pyxel

from game import config
from game.ui import font

POPUP_FRAMES = 18  # ダメージ数値が消えるまで
FLASH_FRAMES = 6  # 攻撃を受けた側の点滅
SHAKE_FRAMES = 10  # 咆哮などの画面の揺れ
SPARKLE_FRAMES = 24  # レベルアップ
SPARKLE_SIZE = 2  # 光の粒の大きさ（px）

COLOR_DAMAGE = 10  # 敵に与えたダメージ
COLOR_PLAYER_DAMAGE = 8  # 受けたダメージ
COLOR_FLASH = 7
COLOR_SPARKLE = 10

Position = tuple[int, int]
ToScreen = Callable[[int, int], Position]


@dataclass
class Popup:
    text: str
    x: int
    y: int
    color: int
    frames: int = POPUP_FRAMES


@dataclass
class EffectLayer:
    """マップ上の演出をまとめて進め、まとめて描く。"""

    popups: list[Popup] = field(default_factory=list)
    flashes: dict[Position, int] = field(default_factory=dict)
    shake_frames: int = 0
    sparkle_frames: int = 0
    sparkle_pos: Position = (0, 0)
    rng: random.Random = field(default_factory=random.Random)

    # --- 追加 ---

    def add_damage(self, x: int, y: int, amount: int, *, on_player: bool = False) -> None:
        color = COLOR_PLAYER_DAMAGE if on_player else COLOR_DAMAGE
        self.popups.append(Popup(str(amount), x, y, color))
        self.flashes[(x, y)] = FLASH_FRAMES

    def add_shake(self) -> None:
        self.shake_frames = SHAKE_FRAMES

    def add_sparkle(self, x: int, y: int) -> None:
        self.sparkle_frames = SPARKLE_FRAMES
        self.sparkle_pos = (x, y)

    # --- 更新 ---

    def update(self) -> None:
        for popup in self.popups:
            popup.frames -= 1
        self.popups = [p for p in self.popups if p.frames > 0]
        self.flashes = {pos: frames - 1 for pos, frames in self.flashes.items() if frames > 1}
        self.shake_frames = max(0, self.shake_frames - 1)
        self.sparkle_frames = max(0, self.sparkle_frames - 1)

    @property
    def offset(self) -> Position:
        """画面の揺れのずれ（px）。"""
        if self.shake_frames <= 0:
            return (0, 0)
        return (self.rng.randint(-4, 4), self.rng.randint(-2, 2))

    def is_flashing(self, x: int, y: int) -> bool:
        return (x, y) in self.flashes

    # --- 描画 ---

    def draw(self, to_screen: ToScreen) -> None:
        if self.sparkle_frames > 0:
            self._draw_sparkle(to_screen)
        for popup in self.popups:
            sx, sy = to_screen(popup.x, popup.y)
            rise = (POPUP_FRAMES - popup.frames) * 2 // 3
            font.draw_text(sx + 2, sy - 8 - rise, popup.text, popup.color)

    def _draw_sparkle(self, to_screen: ToScreen) -> None:
        """レベルアップ: 周りに光の粒が回る。"""
        sx, sy = to_screen(*self.sparkle_pos)
        cx, cy = sx + config.TILE_SIZE // 2, sy + config.TILE_SIZE // 2
        phase = (SPARKLE_FRAMES - self.sparkle_frames) / SPARKLE_FRAMES
        for i in range(6):
            angle = phase * 6.28 + i * 1.05
            radius = 8 + phase * 16
            # 光の粒は 2px 四方にする。1px だと小さすぎて見えにくい
            pyxel.rect(
                cx + int(radius * pyxel.cos(angle * 57.3)),
                cy + int(radius * pyxel.sin(angle * 57.3)),
                SPARKLE_SIZE,
                SPARKLE_SIZE,
                COLOR_SPARKLE,
            )

    def draw_flash(self, sx: int, sy: int) -> None:
        """攻撃を受けた側を白く点滅させる（スプライトの上に重ねる）。"""
        pyxel.dither(0.5)
        pyxel.rect(sx, sy, config.TILE_SIZE, config.TILE_SIZE, COLOR_FLASH)
        pyxel.dither(1.0)
