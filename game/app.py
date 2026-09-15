"""Pyxel の初期化とシーン管理。仕様書 2.1 / 4章。"""

from __future__ import annotations

import pyxel

from game import config, data_loader, rng
from game.entities.player import PLAYER_SPRITE_NAMES
from game.scenes import Scene
from game.scenes.dungeon import DungeonScene
from game.ui import font
from game.ui.input import Controls
from game.ui.sprites import SpriteSheet
from game.world.tiles import SPRITE_NAMES


class App:
    def __init__(self, seed: int | None, display_scale: int, debug: bool) -> None:
        # データや素材の不備は、ウィンドウを開く前に検出する
        self.data = data_loader.load_all()
        sprite_defs = data_loader.parse_sprites(self.data["sprites"])
        data_loader.require_sprites(sprite_defs, [*SPRITE_NAMES.values(), *PLAYER_SPRITE_NAMES])
        if not config.RESOURCE_PATH.exists():
            raise FileNotFoundError(
                f"{config.RESOURCE_PATH} がありません。"
                "tools/make_placeholder_sprites.py を実行して作成してください。"
            )

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
        pyxel.load(str(config.RESOURCE_PATH))
        font.load()

        # フェーズ6でタイトル → 拠点 → ダンジョンの流れにする
        self.scene: Scene = DungeonScene(
            run_seed=self.run_seed,
            data=self.data,
            sprites=SpriteSheet(sprite_defs),
            controls=Controls(float(self.data["balance"]["input"]["repeat_interval_sec"])),
            debug=debug,
        )

    def run(self) -> None:
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        next_scene = self.scene.update()
        if next_scene is not None:
            self.scene = next_scene

    def draw(self) -> None:
        self.scene.draw()
