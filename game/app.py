"""Pyxel の初期化とシーン管理。仕様書 2.1 / 4章。"""

from __future__ import annotations

import pyxel

from game import config, data_loader, rng
from game.entities.player import PLAYER_SPRITE_NAMES
from game.scenes import Scene
from game.scenes.dungeon import DungeonScene
from game.systems.game_state import GameParams, GameState
from game.ui import font
from game.ui.input import Controls
from game.ui.sprites import SpriteSheet
from game.world.tiles import SPRITE_NAMES


class App:
    def __init__(self, seed: int | None, display_scale: int, debug: bool) -> None:
        # データや素材の不備は、ウィンドウを開く前に検出する
        self.data = data_loader.load_all()
        self.params = GameParams.from_data(self.data)
        sprite_defs = data_loader.parse_sprites(self.data["sprites"])
        data_loader.require_sprites(
            sprite_defs,
            [*SPRITE_NAMES.values(), *PLAYER_SPRITE_NAMES, *self.params.catalog.sprite_names()],
        )
        if not config.RESOURCE_PATH.exists():
            raise FileNotFoundError(
                f"{config.RESOURCE_PATH} がありません。"
                "tools/make_placeholder_sprites.py を実行して作成してください。"
            )
        self.debug = debug

        pyxel.init(
            config.SCREEN_WIDTH,
            config.SCREEN_HEIGHT,
            title=config.TITLE,
            fps=config.FPS,
            display_scale=display_scale,
            quit_key=pyxel.KEY_NONE,
        )
        pyxel.load(str(config.RESOURCE_PATH))
        pyxel.mouse(True)
        font.load()

        self.sprites = SpriteSheet(sprite_defs)
        self.controls = Controls(float(self.data["balance"]["input"]["repeat_interval_sec"]))
        # フェーズ6でタイトル → 拠点 → ダンジョンの流れにする
        self.scene: Scene = self.new_run(seed)

    def new_run(self, seed: int | None = None) -> Scene:
        """新しい挑戦を B1F から始める。"""
        state = GameState(seed if seed is not None else rng.new_run_seed(), self.params)
        return DungeonScene(
            state=state,
            sprites=self.sprites,
            controls=self.controls,
            debug=self.debug,
            new_run=self.new_run,
        )

    def run(self) -> None:
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        next_scene = self.scene.update()
        if next_scene is not None:
            self.scene = next_scene

    def draw(self) -> None:
        self.scene.draw()
