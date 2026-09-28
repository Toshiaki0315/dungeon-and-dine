"""主人公の見た目を選ぶ画面。仕様書 6.1。

名前を入力したあとに、戦士・格闘家・魔法使い・僧侶・商人の5種から選ぶ。見た目だけの違いで、能力は変わらない。
"""

from __future__ import annotations

from collections.abc import Callable

import pyxel

from game import config
from game.entities.player import APPEARANCE_IDS, APPEARANCES, player_sprite_name
from game.scenes import Scene
from game.ui import font, mouse
from game.ui.input import Controls
from game.ui.menu import draw_window
from game.ui.sprites import SpriteSheet

COLOR_TITLE = 10
COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_CURSOR = 5

CARD_W, CARD_H, CARD_GAP = 112, 136, 8
CARD_X = (
    config.SCREEN_WIDTH - (CARD_W * len(APPEARANCES) + CARD_GAP * (len(APPEARANCES) - 1))
) // 2
CARD_Y = 72
SPRITE_SCALE = 5  # 16×16 の素材を 80px に拡大する
LABEL_Y = CARD_Y + CARD_H - 28
# 選んでいる見た目は、その場で向きを変えながら歩かせて、全方向の姿を見せる
TURN_ORDER: tuple[str, ...] = ("down", "left", "up", "right")
TURN_FRAMES = config.FPS


class AppearanceSelectScene:
    def __init__(
        self,
        *,
        controls: Controls,
        sprites: SpriteSheet,
        player_name: str,
        current: str,
        on_done: Callable[[str], Scene],
        on_back: Callable[[], Scene],
    ) -> None:
        self.controls = controls
        self.sprites = sprites
        self.player_name = player_name
        self.on_done = on_done
        self.on_back = on_back
        # 開いた直後はどれも選んでいない状態にする（1回のクリックで決まってしまわないように）
        self.index: int | None = None
        self.current = APPEARANCE_IDS.index(current) if current in APPEARANCE_IDS else 0
        self.frames = 0

    def card_rects(self) -> list[mouse.Rect]:
        return [
            (CARD_X + i * (CARD_W + CARD_GAP), CARD_Y, CARD_W, CARD_H)
            for i in range(len(APPEARANCES))
        ]

    def update(self) -> Scene | None:
        c = self.controls
        self.frames += 1
        if c.triggered("cancel") or c.right_clicked():
            return self.on_back()
        click = c.clicked()
        if click is not None:
            index = mouse.index_of(click, self.card_rects())
            if index is not None:
                if index == self.index:  # 選んでいる姿をもう一度クリックすると決まる
                    return self.on_done(APPEARANCE_IDS[index])
                self._select(index)
            return None
        step = int(c.triggered_repeat("right")) - int(c.triggered_repeat("left"))
        if step:
            # まだ選んでいなければ、前回の姿から選び始める
            self._select(
                self.current if self.index is None else (self.index + step) % len(APPEARANCES)
            )
        if c.triggered("confirm"):
            if self.index is None:
                self._select(self.current)  # 1回目の決定は「選ぶ」まで
            else:
                return self.on_done(APPEARANCE_IDS[self.index])
        return None

    def _select(self, index: int) -> None:
        self.index = index
        self.frames = 0  # 選び直したら正面から見せる

    def draw(self) -> None:
        pyxel.cls(0)
        font.draw_text(16, 12, f"{self.player_name}の姿を選んでください", COLOR_TITLE)
        walk = pyxel.frame_count // config.ANIMATION_TICKS
        for i, ((appearance, label), (x, _, _, _)) in enumerate(
            zip(APPEARANCES, self.card_rects(), strict=True)
        ):
            selected = i == self.index
            draw_window(x, CARD_Y, CARD_W, CARD_H)
            if i == self.current and not selected:
                font.draw_text(x + 8, CARD_Y + 6, "前回", COLOR_SUBTEXT)
            if selected:
                pyxel.rectb(x - 2, CARD_Y - 2, CARD_W + 4, CARD_H + 4, COLOR_TITLE)
                pyxel.rect(x + 8, LABEL_Y - 4, CARD_W - 16, config.LINE_HEIGHT + 4, COLOR_CURSOR)
                facing = TURN_ORDER[self.frames // TURN_FRAMES % len(TURN_ORDER)]
                frame = walk
            else:
                facing, frame = "down", 0
            sprite_x = x + (CARD_W - config.SPRITE_SIZE * SPRITE_SCALE) // 2
            name = player_sprite_name(appearance, facing)
            self.sprites.draw_scaled(name, sprite_x, CARD_Y + 16, SPRITE_SCALE, frame)
            label_x = x + (CARD_W - font.text_width(label)) // 2
            font.draw_text(label_x, LABEL_Y, label, COLOR_TEXT if selected else COLOR_SUBTEXT)

        notes = (
            "見た目だけの違いで、能力は変わりません。",
            "選んでから、もう一度クリック（または決定）で決まります。"
            if self.index is None
            else "タイトルの「はじめる」から選び直せます。",
        )
        for i, note in enumerate(notes):
            font.draw_text_centered(
                CARD_Y + CARD_H + 32 + i * config.LINE_HEIGHT, note, COLOR_SUBTEXT
            )
        hint = "←→/クリック: 選ぶ  決定・もう一度クリック: 決める  Esc / 右クリック: 戻る"
        font.draw_text_centered(config.SCREEN_HEIGHT - 24, hint, COLOR_SUBTEXT)
