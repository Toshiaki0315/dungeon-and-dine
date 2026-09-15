"""Pyxel の初期化とシーン管理。仕様書 2.1 / 4章。"""

from __future__ import annotations

import pyxel

from game import config, rng
from game.scenes import Scene
from game.ui import font


class BootScene:
    """開発開始用の仮シーン。フェーズ1で TitleScene / DungeonScene に置き換える。"""

    def __init__(self, app: App) -> None:
        self.app = app

    def update(self) -> Scene | None:
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()
        return None

    def draw(self) -> None:
        pyxel.cls(0)
        if font.is_japanese_available():
            font.draw_text(8, 8, "Dungeon & Dine: 飢餓のトレジャーハンター", 7)
            font.draw_text(8, 24, "開発環境の準備ができました（Escで終了）", 6)
        else:
            font.draw_text(8, 8, "Dungeon & Dine", 7)
            font.draw_text(8, 24, "Font not found: assets/fonts/misaki_gothic_2nd.bdf", 8)
        font.draw_text(8, 40, f"seed: {self.app.run_seed}", 5)


class App:
    def __init__(self, seed: int | None, display_scale: int, debug: bool) -> None:
        self.run_seed: int = seed if seed is not None else rng.new_run_seed()
        self.debug = debug

        pyxel.init(
            config.SCREEN_WIDTH,
            config.SCREEN_HEIGHT,
            title=config.TITLE,
            fps=config.FPS,
            display_scale=display_scale,
            quit_key=pyxel.KEY_NONE,
        )
        font.load()
        if config.RESOURCE_PATH.exists():
            pyxel.load(str(config.RESOURCE_PATH))

        self.scene: Scene = BootScene(self)

    def run(self) -> None:
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        next_scene = self.scene.update()
        if next_scene is not None:
            self.scene = next_scene

    def draw(self) -> None:
        self.scene.draw()
