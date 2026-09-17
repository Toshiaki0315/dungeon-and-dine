"""料理カットイン（ワイプ・パレット入れ替え・演出）。仕様書 2.4 / 9.3。

段階1 切り替え → 2 食材選択 → 3 調理演出 → 4 結果表示 → 5 復帰、の順に進む。
カットインの間だけ `pyxel.colors` を料理用のパレットに入れ替え、閉じるときに元へ戻す。
"""

from __future__ import annotations

import random
from enum import Enum, auto

import pyxel

from game import config
from game.systems.cooking import HEAT_STOVE, CutinSettings, describe_effects
from game.systems.game_state import CookPlan, GameState
from game.ui import font
from game.ui.cooking_view import CANCELLED, CookingView
from game.ui.input import Controls

# 背景の素材は等倍 320×140（tools/make_cutin_background.py が作る）。画面へは ART_SCALE 倍に拡大し、
# 文字の窓（下部 TEXT_WINDOW_H）より上の領域の縦中央に置く。絵の上下は暗い色の帯で埋める。
ART_W, ART_H, ART_SCALE = 320, 140, 2
TEXT_WINDOW_H = 80  # 仕様書 2.4 の「下部 320×40 のテキストウィンドウ」を2倍にした高さ
CUTIN_HEIGHT = config.SCREEN_HEIGHT - TEXT_WINDOW_H
ART_TOP = (CUTIN_HEIGHT - ART_H * ART_SCALE) // 2
TEXT_TOP = CUTIN_HEIGHT
GROUND_TOP = ART_TOP + 104 * ART_SCALE

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_DISH = 11
COLOR_DARK = 1
COLOR_CAVE = 2
COLOR_GROUND = 4
COLOR_STONE = 5
COLOR_FIRE = 9
COLOR_FIRE_LIGHT = 10
COLOR_STOVE = 12
COLOR_STEAM = 6
COLOR_HAND = 14
MEAT_COLORS = (14, 15, 4)  # 生 → 焼き色1 → 焼き色2

STEAM_MAX = 24


class Phase(Enum):
    WIPE_IN = auto()  # 段階1
    SELECT = auto()  # 段階2
    COOKING = auto()  # 段階3
    RESULT = auto()  # 段階4
    WIPE_OUT = auto()  # 段階5
    DONE = auto()


class CookingCutin:
    def __init__(
        self,
        state: GameState,
        settings: CutinSettings,
        palette: list[int],
        backgrounds: dict[str, pyxel.Image] | None = None,
    ) -> None:
        self.state = state
        self.settings = settings
        self.palette = palette
        self.backgrounds = backgrounds or {}
        self.view = CookingView(state)
        self.phase = Phase.DONE
        self.plan: CookPlan | None = None
        self.frames = 0
        self._saved_palette: list[int] = []
        self._rng = random.Random()
        self._steam: list[list[float]] = []  # [x, y, 残りの寿命]

    # --- 進行 ---

    @property
    def active(self) -> bool:
        return self.phase != Phase.DONE

    @property
    def shows_cutin(self) -> bool:
        """このフレームでカットインを描くか。ワイプの途中で探索画面と入れ替わる。"""
        if self.phase in (Phase.SELECT, Phase.COOKING, Phase.RESULT):
            return True
        if self.phase == Phase.WIPE_IN:
            return self._progress() >= 0.5
        if self.phase == Phase.WIPE_OUT:
            return self._progress() < 0.5
        return False

    def open(self) -> None:
        """料理コマンドから開く。"""
        self.view.open()
        self.plan = None
        self._steam.clear()
        if self.settings.skip_wipe:
            self._enter_palette()
            self._start(Phase.SELECT)
        else:
            self._start(Phase.WIPE_IN)

    def update(self, controls: Controls) -> CookPlan | None:
        """進める。実際に調理する（1ターン使う）タイミングで、その内容を返す。"""
        self.frames += 1
        if self.phase == Phase.WIPE_IN:
            if self._passed_midpoint():
                self._enter_palette()
            if self._phase_done():
                self._start(Phase.SELECT)
        elif self.phase == Phase.SELECT:
            return self._update_select(controls)
        elif self.phase == Phase.COOKING:
            self._update_steam()
            if self._phase_done():
                self._start(Phase.RESULT)
        elif self.phase == Phase.RESULT:
            self._update_steam()
            if controls.triggered("confirm") or controls.triggered("cancel"):
                return self._leave()
        elif self.phase == Phase.WIPE_OUT:
            self._update_steam()
            if self._passed_midpoint():
                # 画面が黒くなったところでパレットを戻し、ここで1ターン経過させる
                self._restore_palette()
                plan, self.plan = self.plan, None
                if plan is not None:
                    return plan
            if self._phase_done():
                self.phase = Phase.DONE
        return None

    def _update_select(self, controls: Controls) -> CookPlan | None:
        result = self.view.update(controls)
        if result == CANCELLED:
            return self._leave()  # ターンを消費せずに戻る
        if isinstance(result, list):
            plan = self.state.plan_cooking(result)
            if plan is not None:
                self.plan = plan
                self._start(Phase.COOKING)
        return None

    def _leave(self) -> CookPlan | None:
        """段階5へ移る。ワイプを省略する設定なら、その場で終わる。"""
        if not self.settings.skip_wipe:
            self._start(Phase.WIPE_OUT)
            return None
        self._restore_palette()
        self.phase = Phase.DONE
        plan, self.plan = self.plan, None
        return plan

    # --- 時間 ---

    def _start(self, phase: Phase) -> None:
        self.phase = phase
        self.frames = 0

    def _phase_frames(self) -> int:
        if self.phase in (Phase.WIPE_IN, Phase.WIPE_OUT):
            seconds = self.settings.wipe_seconds
        elif self.phase == Phase.COOKING:
            seconds = (
                self.settings.short_cooking_seconds
                if self.settings.short_cooking
                else self.settings.cooking_seconds
            )
        else:
            return 0
        return max(1, round(seconds * config.FPS))

    def _progress(self) -> float:
        frames = self._phase_frames()
        return 1.0 if frames <= 0 else min(1.0, self.frames / frames)

    def _phase_done(self) -> bool:
        return self.frames >= self._phase_frames()

    def _passed_midpoint(self) -> bool:
        frames = self._phase_frames()
        if frames <= 0:
            return True
        return (self.frames - 1) / frames < 0.5 <= self.frames / frames

    # --- パレット ---

    def _enter_palette(self) -> None:
        if self._saved_palette or not self.palette:
            return
        self._saved_palette = list(pyxel.colors)
        pyxel.colors[:] = self.palette

    def _restore_palette(self) -> None:
        if self._saved_palette:
            pyxel.colors[:] = self._saved_palette
            self._saved_palette = []

    # --- 描画 ---

    def draw(self) -> None:
        """カットイン画面（背景・演出・ウィンドウ）を描く。"""
        self._draw_background()
        self._draw_fire()
        self._draw_food()
        self._draw_steam()
        if self.phase == Phase.SELECT:
            self.view.draw()
        self._draw_text_window()
        self.draw_overlay()

    def draw_overlay(self) -> None:
        """ワイプの覆い。探索画面の上に重ねるときにも使う。"""
        alpha = self._wipe_alpha()
        if alpha <= 0:
            return
        pyxel.dither(alpha)
        pyxel.rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT, 0)
        pyxel.dither(1.0)

    def _wipe_alpha(self) -> float:
        if self.phase not in (Phase.WIPE_IN, Phase.WIPE_OUT):
            return 0.0
        t = self._progress()
        return 2 * t if t < 0.5 else 2 - 2 * t

    def _draw_background(self) -> None:
        width = config.SCREEN_WIDTH
        art_bottom = ART_TOP + ART_H * ART_SCALE
        pyxel.rect(0, 0, width, CUTIN_HEIGHT, COLOR_DARK)  # 絵の上下の帯
        image = self.backgrounds.get(self.state.area.id) or self.backgrounds.get("default")
        if image is not None:
            # blt の scale は中心基準なので、左上が (0, ART_TOP) に来るようずらす
            w, h = image.width, image.height
            ox, oy = w * (ART_SCALE - 1) // 2, h * (ART_SCALE - 1) // 2
            pyxel.blt(ox, ART_TOP + oy, image, 0, 0, w, h, scale=ART_SCALE)
            return
        # 仮の背景: 単色と簡単な図形で、焚き火を囲む洞窟を描く（素材がないエリアで使う）。
        # 等倍の素材と同じ構図を ART_SCALE 倍にした座標。上下の帯にはみ出さないよう絵の範囲で切る
        pyxel.clip(0, ART_TOP, width, ART_H * ART_SCALE)
        pyxel.dither(0.5)
        pyxel.rect(0, ART_TOP + 48, width, GROUND_TOP - ART_TOP - 48, COLOR_CAVE)
        pyxel.dither(1.0)
        pyxel.elli(-80, ART_TOP - 120, 400, 300, COLOR_CAVE)
        pyxel.elli(width - 320, ART_TOP - 140, 400, 300, COLOR_CAVE)
        pyxel.rect(0, GROUND_TOP, width, art_bottom - GROUND_TOP, COLOR_GROUND)
        pyxel.dither(0.5)
        pyxel.rect(0, GROUND_TOP, width, 12, COLOR_STONE)
        pyxel.dither(1.0)
        for x in (72, 300, 536):
            pyxel.elli(x, GROUND_TOP + 24, 52, 24, COLOR_STONE)
        pyxel.clip()

    def _draw_fire(self) -> None:
        """焚き火（または携帯コンロ）と、3コマで揺れる炎。"""
        cx, base = config.SCREEN_WIDTH // 2, GROUND_TOP + 4
        frame = pyxel.frame_count // 4 % 3
        if self.plan is not None and self.plan.heat == HEAT_STOVE:
            pyxel.rect(cx - 32, base - 12, 64, 24, COLOR_STOVE)
            pyxel.rect(cx - 24, base - 20, 48, 8, COLOR_STONE)
        else:
            pyxel.rect(cx - 40, base - 4, 80, 12, COLOR_GROUND)
            pyxel.rect(cx - 28, base - 12, 56, 10, COLOR_STONE)
        sway = (-4, 0, 4)[frame]
        pyxel.tri(cx - 24, base - 12, cx + 24, base - 12, cx + sway, base - 68, COLOR_FIRE)
        pyxel.tri(cx - 12, base - 12, cx + 12, base - 12, cx + sway, base - 44, COLOR_FIRE_LIGHT)

    def _draw_food(self) -> None:
        """串の肉（焼き色が2段階で変わる）と、レオの手元（2コマ）。"""
        if self.phase not in (Phase.COOKING, Phase.RESULT, Phase.WIPE_OUT):
            return
        cx, base = config.SCREEN_WIDTH // 2, GROUND_TOP + 4
        stage = 0
        if self.phase == Phase.COOKING and self._progress() >= 0.5:
            stage = 1
        elif self.phase != Phase.COOKING:
            stage = 2
        # 串は 2px の太さにする（1px だと拡大した画面では細すぎる）
        for dy in (0, 1):
            pyxel.line(cx - 52, base - 52 + dy, cx + 52, base - 60 + dy, COLOR_GROUND)
        for i in range(3):
            pyxel.elli(cx - 32 + i * 24, base - 64 + i * 2, 20, 16, MEAT_COLORS[stage])
        hand = pyxel.frame_count // 8 % 2
        pyxel.rect(cx + 52, base - 64 + hand * 2, 20, 12, COLOR_HAND)

    def _update_steam(self) -> None:
        """湯気のパーティクルを立ち上らせる。"""
        cx = config.SCREEN_WIDTH // 2
        if len(self._steam) < STEAM_MAX and self._rng.random() < 0.5:
            self._steam.append([cx + self._rng.uniform(-36, 36), GROUND_TOP - 60, 1.0])
        for particle in self._steam:
            particle[1] -= 1.6
            particle[0] += self._rng.uniform(-0.8, 0.8)
            particle[2] -= 0.02
        self._steam[:] = [p for p in self._steam if p[2] > 0]

    def _draw_steam(self) -> None:
        for x, y, life in self._steam:
            pyxel.dither(max(0.0, min(1.0, life)) * 0.6)
            pyxel.circ(x, y, 4, COLOR_STEAM)
        pyxel.dither(1.0)

    def _draw_text_window(self) -> None:
        pyxel.rect(0, TEXT_TOP, config.SCREEN_WIDTH, config.SCREEN_HEIGHT - TEXT_TOP, 0)
        pyxel.line(0, TEXT_TOP, config.SCREEN_WIDTH - 1, TEXT_TOP, COLOR_SUBTEXT)
        lines = self._text_lines()
        for i, (text, color) in enumerate(lines[:3]):
            font.draw_text(12, TEXT_TOP + 8 + i * config.LINE_HEIGHT, text, color)

    def _text_lines(self) -> list[tuple[str, int]]:
        name = self.state.player.name
        if self.phase == Phase.SELECT:
            return [
                ("材料を2〜3個選んでください。", COLOR_TEXT),
                ("決定: 選ぶ／外す  C: 調理する  Esc: やめる", COLOR_SUBTEXT),
            ]
        plan = self.plan
        if plan is None:
            return []
        materials = "・".join(m.definition.name for m in plan.materials)
        if self.phase == Phase.COOKING:
            return [(f"{name}は{materials}を焼いている……", COLOR_TEXT)]
        if plan.recipe is not None:
            effects = describe_effects(
                plan.recipe.effects, {s.id: s.name for s in self.state.catalog.statuses.values()}
            )
            return [
                (f"{plan.product.name}ができた！", COLOR_DISH),
                (effects, COLOR_TEXT),
                ("決定: 戻る", COLOR_SUBTEXT),
            ]
        return [
            (f"{plan.product.name}ができた……", COLOR_TEXT),
            ("決定: 戻る", COLOR_SUBTEXT),
        ]
