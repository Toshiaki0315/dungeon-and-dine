"""Pyxel の初期化とシーン管理。仕様書 2.1 / 4章 / 13章。"""

from __future__ import annotations

import atexit
from pathlib import Path
from typing import Any

import pyxel

from game import config, data_loader, rng
from game.entities.player import PLAYER_SPRITE_NAMES
from game.scenes import Scene
from game.scenes.base_camp import BaseCampScene
from game.scenes.dungeon import DungeonScene
from game.scenes.ending import EndingScene
from game.scenes.game_over import GameOverScene
from game.scenes.name_input import NameInputScene
from game.scenes.title import TitleScene
from game.systems import save
from game.systems.game_state import GameParams, GameState
from game.ui import font
from game.ui.audio import Audio
from game.ui.input import Controls
from game.ui.sprites import SpriteSheet
from game.world.tiles import CAMPFIRE_SPRITE, SAFE_FLOOR_SPRITE, SPRITE_NAMES


class App:
    def __init__(self, seed: int | None, display_scale: int, debug: bool) -> None:
        # データや素材の不備は、ウィンドウを開く前に検出する
        self.data = data_loader.load_all()
        self.params = GameParams.from_data(self.data)
        sprite_defs = data_loader.parse_sprites(self.data["sprites"])
        data_loader.require_sprites(
            sprite_defs,
            [
                *SPRITE_NAMES.values(),
                *PLAYER_SPRITE_NAMES,
                CAMPFIRE_SPRITE,
                SAFE_FLOOR_SPRITE,
                *self.params.catalog.sprite_names(),
            ],
        )
        self.cooking_palette = _parse_palette(self.data["palettes"], "cooking")
        if not config.RESOURCE_PATH.exists():
            raise FileNotFoundError(
                f"{config.RESOURCE_PATH} がありません。"
                "tools/make_placeholder_sprites.py を実行して作成してください。"
            )
        self.debug = debug
        self.seed = seed

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
        self.cutin_backgrounds = _load_cutin_backgrounds()
        self.audio = Audio(self.data["sounds"])
        self.controls = Controls(float(self.data["balance"]["input"]["repeat_interval_sec"]))

        # セーブデータ（保存先は OS ごとのユーザーデータフォルダ。仕様書 13章）
        self.save_dir = Path(pyxel.user_data_dir(config.APP_ID, config.APP_ID))
        self.camp_params = self.params.base_camp
        self.meta = save.load_meta(self.save_dir, self.params, self.camp_params)
        self.run_state: GameState | None = None
        atexit.register(self._save_on_exit)

        self.scene: Scene = self.title()

    # --- シーンの生成と遷移（仕様書 4章） ---

    def title(self) -> Scene:
        self.audio.play_bgm("title")
        return TitleScene(
            controls=self.controls,
            sprites=self.sprites,
            meta=self.meta,
            start=self.name_input,
            resume=self.resume_run,
            quit_game=pyxel.quit,
            has_run=save.run_exists(self.save_dir),
        )

    def name_input(self) -> Scene:
        """はじめるときに主人公の名前を入力する（仕様書 6.1）。"""
        return NameInputScene(
            controls=self.controls,
            meta=self.meta,
            sprites=self.sprites,
            on_done=self._name_decided,
        )

    def _name_decided(self, name: str) -> Scene:
        self.meta.player_name = name
        self.save_meta()
        return self.base_camp(f"{name}、迷宮へようこそ。")

    def base_camp(self, message: str = "") -> Scene:
        self.audio.play_bgm("camp")
        return BaseCampScene(
            controls=self.controls,
            sprites=self.sprites,
            meta=self.meta,
            params=self.camp_params,
            catalog=self.params.catalog,
            depart=self.new_run,
            save_meta=self.save_meta,
            message=message,
        )

    def new_run(self, seed: int | None = None) -> Scene:
        """拠点から新しい挑戦に出発する。持ち物と装備はそのまま持って行く。"""
        run_seed = seed if seed is not None else self.seed
        state = GameState(
            run_seed if run_seed is not None else rng.new_run_seed(),
            self.params,
            self.meta.notebook,
        )
        state.player.name = self.meta.player_name
        state.take_loadout(self.meta.loadout)
        self.meta.loadout.clear()  # 持ち込んだので、拠点には残らない
        self.save_meta()
        return self.dungeon(state, autosave=True)

    def resume_run(self) -> Scene | None:
        """「つづきから」。読み込んだ直後に run.json を消す（仕様書 13章）。"""
        state = save.load_run(self.save_dir, self.params, self.meta.notebook)
        if state is None:
            return None
        save.delete_run(self.save_dir)
        return self.dungeon(state, autosave=False)

    def dungeon(self, state: GameState, *, autosave: bool) -> Scene:
        self.run_state = state
        self.audio.play_bgm(state.area.id)
        if autosave:
            self.autosave(state)
        return DungeonScene(
            state=state,
            sprites=self.sprites,
            controls=self.controls,
            debug=self.debug,
            finish_run=self.finish_run,
            show_ending=self.show_ending,
            save_run=self.autosave,
            cooking_palette=self.cooking_palette,
            cutin_backgrounds=self.cutin_backgrounds,
            audio=self.audio,
        )

    def show_ending(self, state: GameState) -> Scene:
        """エンディングの階のボスを倒したときの演出（仕様書 8.3）。

        迷宮に最下層はないので、挑戦はここで終わらない。見たあと、さらに潜るか帰還するかを選ぶ。
        """
        self.meta.clears += 1
        self.meta.record_run(state.floor.number)
        self.save_meta()
        return EndingScene(
            player_name=state.player.name,
            boss_name=state.last_boss_name,
            floor_number=state.floor.number,
            turn=state.turn,
            level=state.player.level,
            clears=self.meta.clears,
            controls=self.controls,
            sprites=self.sprites,
            to_camp=lambda: self.finish_run(state, True),
            to_dungeon=lambda: self.dungeon(state, autosave=True),
        )

    def finish_run(self, state: GameState, survived: bool) -> Scene:
        """挑戦の終わり（死亡・生還）。引き継ぎを行い、中断データを消す（仕様書 12.3）。"""
        self.meta.finish_run(
            survived=survived,
            items=list(state.inventory.items),
            equipment=dict(state.player.equipment),
            gold=state.player.gold,
            floor_number=state.floor.number,
            turn=state.turn,
            cleared=state.cleared,
        )
        self.run_state = None
        save.delete_run(self.save_dir)
        self.save_meta()
        if survived:
            return self.base_camp(f"{state.player.name}は {state.player.gold}G を持ち帰った。")
        return GameOverScene(
            player_name=state.player.name,
            floor_number=state.floor.number,
            turn=state.turn,
            controls=self.controls,
            to_camp=self.base_camp,
            meta=self.meta,
            latest=self.meta.scores[-1] if self.meta.scores else None,
        )

    # --- セーブ ---

    def autosave(self, state: GameState) -> None:
        save.save_run(self.save_dir, state)
        self.save_meta()  # レシピ手帳の発見もここで残す

    def save_meta(self) -> None:
        save.save_meta(self.save_dir, self.meta)

    def _save_on_exit(self) -> None:
        """ウィンドウを閉じたときに、挑戦中のデータを保存する（仕様書 13章）。"""
        if self.run_state is not None and not self.run_state.run_over:
            save.save_run(self.save_dir, self.run_state)
        self.save_meta()

    # --- メインループ ---

    def run(self) -> None:
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        next_scene = self.scene.update()
        if next_scene is not None:
            self.scene = next_scene

    def draw(self) -> None:
        self.scene.draw()


def _parse_palette(data: dict[str, Any], name: str) -> list[int]:
    """palettes.json の16色（"rrggbb"）を Pyxel の色に変換する。"""
    palettes = data["palettes"]
    assert isinstance(palettes, dict)
    if name not in palettes:
        raise data_loader.DataValidationError(f"palettes.json: {name} がありません")
    colors = palettes[name]
    if len(colors) != pyxel.NUM_COLORS:
        raise data_loader.DataValidationError(
            f"palettes.json: {name} は{pyxel.NUM_COLORS}色で定義してください"
        )
    return [int(color, 16) for color in colors]


def _load_cutin_backgrounds() -> dict[str, pyxel.Image]:
    """assets/cutins/cooking_<エリアID>.png を読み込む。なければ仮の背景を描く。"""
    backgrounds: dict[str, pyxel.Image] = {}
    if not config.CUTIN_DIR.exists():
        return backgrounds
    for path in sorted(config.CUTIN_DIR.glob("cooking_*.png")):
        backgrounds[path.stem.removeprefix("cooking_")] = pyxel.Image.from_image(str(path))
    return backgrounds
