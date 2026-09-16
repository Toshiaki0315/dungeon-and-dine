"""ダンジョン探索シーン。仕様書 4章。

ゲームの状態とターン進行は systems/game_state.py が持ち、このシーンは入力と描画を担当する。
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto

import pyxel

from game import config
from game.entities.item import ItemInstance
from game.scenes import Scene
from game.systems.game_state import (
    EFFECT_CURSE,
    EFFECT_HIT,
    EFFECT_LEVEL_UP,
    EFFECT_ROAR,
    EquipResult,
    GameEvent,
    GameState,
    MoveResult,
)
from game.systems.progression import exp_to_next_level
from game.ui import font, hud, minimap
from game.ui.audio import Audio
from game.ui.camera import camera_origin
from game.ui.command_bar import COMMANDS, CommandBar, command_label, hit_test
from game.ui.cooking_cutin import CookingCutin
from game.ui.effects import EffectLayer
from game.ui.equipment_view import EquipmentView, EquipRequest
from game.ui.input import Controls, MoveCommand, TurnCommand
from game.ui.inventory_view import (
    ACTION_DROP,
    ACTION_EQUIP,
    ACTION_TARGET,
    ACTION_THROW,
    ACTION_UNEQUIP,
    InventoryView,
    ItemRequest,
)
from game.ui.log import LogHistoryView, draw_recent
from game.ui.menu import ConfirmDialog
from game.ui.notebook_view import NotebookView
from game.ui.skill_view import SkillView
from game.ui.sprites import SpriteSheet
from game.world.direction import Direction
from game.world.fov import Visibility
from game.world.tiles import CAMPFIRE_SPRITE, SAFE_FLOOR_SPRITE, SPRITE_NAMES, Tile

FLOOR_BANNER_SECONDS = 2
CURSE_FLASH_FRAMES = config.FPS

COLOR_TEXT = 7
COLOR_SUBTEXT = 13
COLOR_FRAME = 1
COLOR_DEBUG = 10
COLOR_STATUS = 14
COLOR_CURSE = 2  # 紫

# 既知タイル（視界外）を暗く描くためのパレット置き換え（仕様書 2.3.1）
KNOWN_TILE_PALETTE: dict[int, int] = {
    1: 0, 2: 1, 3: 1, 4: 2, 5: 1, 6: 5, 7: 13, 8: 2,
    9: 4, 10: 9, 11: 3, 12: 5, 13: 5, 14: 8, 15: 4,
}  # fmt: skip

# ショートカットキー → コマンドID（仕様書 3.2）
SHORTCUTS: dict[str, str] = {
    "inventory": "items",
    "skills": "skills",
    "cook": "cook",
    "equipment": "equipment",
    "map": "map",
}


class Mode(Enum):
    """ダンジョン内のサブモード。EXPLORE 以外を開いている間はターンが進まない。"""

    EXPLORE = auto()
    COMMAND_BAR = auto()
    INVENTORY = auto()  # 対象の選択（ITEM の対象・目利き）もこの画面で行う
    EQUIPMENT = auto()
    SKILL_MENU = auto()
    COOKING_CUTIN = auto()  # 食材選択 → 調理演出 → 結果表示（仕様書 9.3）
    NOTEBOOK = auto()
    FULL_MAP = auto()
    CONFIRM = auto()
    LOG_HISTORY = auto()


class DungeonScene:
    def __init__(
        self,
        *,
        state: GameState,
        sprites: SpriteSheet,
        controls: Controls,
        debug: bool,
        finish_run: Callable[[GameState, bool], Scene],
        save_run: Callable[[GameState], None] | None = None,
        cooking_palette: list[int] | None = None,
        cutin_backgrounds: dict[str, pyxel.Image] | None = None,
        audio: Audio | None = None,
    ) -> None:
        self.state = state
        self.sprites = sprites
        self.controls = controls
        self.debug = debug
        self.finish_run = finish_run
        self.save_run = save_run
        self.show_debug = False

        self.mode = Mode.EXPLORE
        self.command_bar = CommandBar()
        self.dialog: ConfirmDialog | None = None
        self.log_history = LogHistoryView(state.log)
        self.inventory_view = InventoryView(state.inventory, state.player.is_equipped)
        self.equipment_view = EquipmentView(state)
        self.skill_view = SkillView()
        self.cutin = CookingCutin(
            state, state.params.cooking.cutin, cooking_palette or [], cutin_backgrounds
        )
        self.notebook_view = NotebookView(state.catalog, state.notebook)
        self.audio = audio
        self.effects = EffectLayer()
        # 対象の選択を待っているアイテム（"item"）またはスキル（"skill"）
        self.pending_target: tuple[str, ItemInstance | str] | None = None
        self.banner_frames = FLOOR_BANNER_SECONDS * config.FPS
        self.curse_flash_frames = 0
        self._last_floor = state.floor.number

    # --- update ---

    def update(self) -> Scene | None:
        # 押しっぱなしの判定を保つため、方向入力はモードにかかわらず毎フレーム読む
        direction_command = self.controls.direction_command()
        if self.debug and self.controls.triggered("debug"):
            self.show_debug = not self.show_debug
        self.banner_frames = max(0, self.banner_frames - 1)
        self.curse_flash_frames = max(0, self.curse_flash_frames - 1)

        if self.mode in (Mode.EXPLORE, Mode.COMMAND_BAR) and self._handle_click():
            pass
        elif self.mode == Mode.EXPLORE:
            self._update_explore(direction_command)
        elif self.mode == Mode.COMMAND_BAR:
            self._update_command_bar()
        elif self.mode == Mode.INVENTORY:
            self._update_inventory()
        elif self.mode == Mode.EQUIPMENT:
            self._update_equipment()
        elif self.mode == Mode.SKILL_MENU:
            self._update_skill_menu()
        elif self.mode == Mode.COOKING_CUTIN:
            self._update_cutin()
        elif self.mode == Mode.NOTEBOOK and self.notebook_view.update(self.controls):
            self.mode = Mode.EXPLORE
        elif self.mode == Mode.FULL_MAP:
            self._close_on("map")
        elif self.mode == Mode.CONFIRM:
            self._update_dialog()
        elif self.mode == Mode.LOG_HISTORY and self.log_history.update(self.controls):
            self.mode = Mode.EXPLORE

        # 敵を見つけた・ダメージを受けたなどで、押しっぱなしの連続移動を止める
        if self.state.consume_interrupt():
            self.controls.interrupt_repeat()
        self.effects.update()
        for event in self.state.consume_events():
            self._handle_event(event)
        if self.state.floor.number != self._last_floor:
            self._last_floor = self.state.floor.number
            self.banner_frames = FLOOR_BANNER_SECONDS * config.FPS
            if self.audio is not None:
                self.audio.play_bgm(self.state.area.id)
            if self.save_run is not None:
                self.save_run(self.state)  # 階を移ったら中断データを保存する（仕様書 13章）

        if self.state.run_over:
            # クリアも生還と同じ扱い（所持品と所持金を持ち帰る）
            return self.finish_run(self.state, self.state.returned or self.state.cleared)
        return None

    def _handle_event(self, event: GameEvent) -> None:
        """ゲーム側の出来事を、効果音と画面の演出にする（仕様書 14章）。"""
        if self.audio is not None:
            self.audio.play_se(event.kind)
        if event.kind == EFFECT_CURSE:
            self.curse_flash_frames = CURSE_FLASH_FRAMES
        elif event.kind == EFFECT_ROAR:
            self.effects.add_shake()
        elif event.kind == EFFECT_HIT and event.x >= 0:
            self.effects.add_damage(event.x, event.y, event.value, on_player=event.on_player)
        elif event.kind == EFFECT_LEVEL_UP and event.x >= 0:
            self.effects.add_sparkle(event.x, event.y)

    def _update_explore(self, direction_command: MoveCommand | TurnCommand | None) -> None:
        c = self.controls
        if c.triggered("command_bar"):
            self.mode = Mode.COMMAND_BAR
            return
        for action, command_id in SHORTCUTS.items():
            if c.triggered(action):
                self._execute_command(command_id)
                return
        if c.triggered("log_history"):
            self.log_history.open()
            self.mode = Mode.LOG_HISTORY
            return
        if c.triggered("notebook"):
            self.notebook_view.open()
            self.mode = Mode.NOTEBOOK
            return
        if c.triggered("confirm"):
            if c.pressed("diagonal_modifier"):
                self.state.wait()  # LB＋A（Shift＋決定）は足踏み
            elif self.state.player_on_stairs:
                self._confirm_descend()
            else:
                self.state.attack()
            return
        if c.triggered("wait"):
            self.state.wait()
            return

        if isinstance(direction_command, MoveCommand):
            self._move(direction_command.direction)
        elif isinstance(direction_command, TurnCommand):
            self.state.face(direction_command.direction)

    def _move(self, direction: Direction) -> None:
        if self.state.move_player(direction) != MoveResult.CONFIRM_TRAP:
            return
        self.controls.interrupt_repeat()
        self._confirm(
            "罠がある。本当に乗りますか？",
            lambda: self.state.move_player(direction, confirm_trap=True),
        )

    def _update_command_bar(self) -> None:
        c = self.controls
        if c.triggered("cancel") or c.triggered("command_bar"):
            self.mode = Mode.EXPLORE
        elif c.triggered_repeat("left"):
            self.command_bar.move(-1)
        elif c.triggered_repeat("right"):
            self.command_bar.move(1)
        elif c.triggered("confirm"):
            self.mode = Mode.EXPLORE
            self._execute_command(self.command_bar.selected.id)

    def _handle_click(self) -> bool:
        position = self.controls.clicked()
        index = hit_test(*position) if position is not None else None
        if index is None:
            return False
        self.command_bar.index = index
        self.mode = Mode.EXPLORE
        self._execute_command(COMMANDS[index].id)
        return True

    def _update_inventory(self) -> None:
        result = self.inventory_view.update(self.controls)
        if result is True:
            self.pending_target = None
            self.mode = Mode.EXPLORE
            return
        if not isinstance(result, ItemRequest):
            return
        self.mode = Mode.EXPLORE
        item = result.item
        if result.kind == ACTION_TARGET:
            self._use_on_target(item)
        elif result.kind == ACTION_THROW:
            self.state.throw_item(item)
        elif result.kind == ACTION_DROP:
            self.state.drop_item(item)
        elif result.kind == ACTION_EQUIP:
            self._equip(item)
        elif result.kind == ACTION_UNEQUIP:
            self.state.unequip(item)
        else:
            self._use_item(item)

    def _update_equipment(self) -> None:
        result = self.equipment_view.update(self.controls)
        if result is True:
            self.mode = Mode.EXPLORE
        elif isinstance(result, EquipRequest):
            self.mode = Mode.EXPLORE
            if result.item is not None:
                self._equip(result.item)
                return
            current = self.state.player.equipment[result.slot]
            if current is not None:
                self.state.unequip(current)

    def _update_cutin(self) -> None:
        plan = self.cutin.update(self.controls)
        if plan is not None:
            self.state.apply_cooking(plan)  # 段階5: ここで1ターン経過する
        if not self.cutin.active:
            self.mode = Mode.EXPLORE

    def _update_skill_menu(self) -> None:
        result = self.skill_view.update(self.controls)
        if result is True:
            self.mode = Mode.EXPLORE
        elif isinstance(result, str):
            self.mode = Mode.EXPLORE
            self._use_skill(result)

    def _use_item(self, item: ItemInstance) -> None:
        targets = self.state.item_targets(item)
        if targets is None:
            self.state.use_item(item)
        elif not targets:
            self.state.log.add("対象にできる装備を持っていない。")
        else:
            self.pending_target = ("item", item)
            self.inventory_view.open_selection("どれに使う？", targets)
            self.mode = Mode.INVENTORY

    def _use_skill(self, skill_id: str) -> None:
        targets = self.state.skill_targets(skill_id)
        if targets is None:
            self.state.use_skill(skill_id)
        elif not targets:
            self.state.log.add("見定められる装備を持っていない。")
        else:
            self.pending_target = ("skill", skill_id)
            self.inventory_view.open_selection("どれを見定める？", targets)
            self.mode = Mode.INVENTORY

    def _use_on_target(self, target: ItemInstance) -> None:
        pending, self.pending_target = self.pending_target, None
        if pending is None:
            return
        kind, source = pending
        if kind == "item" and isinstance(source, ItemInstance):
            self.state.use_item(source, target)
        elif isinstance(source, str):
            self.state.use_skill(source, target)

    def _equip(self, item: ItemInstance) -> None:
        if self.state.equip(item) != EquipResult.NEEDS_CONFIRM:
            return
        if item.curse_known and item.cursed:
            message = "呪われた装備です。装備しますか？"
        else:
            message = "正体のわからない装備です。装備しますか？"
        self._confirm(message, lambda: self.state.equip(item, confirmed=True))

    def _confirm(self, message: str, on_yes: Callable[[], object]) -> None:
        self.dialog = ConfirmDialog(message, on_yes)
        self.mode = Mode.CONFIRM

    def _close_on(self, toggle_action: str) -> None:
        if self.controls.triggered("cancel") or self.controls.triggered(toggle_action):
            self.mode = Mode.EXPLORE

    def _update_dialog(self) -> None:
        if self.dialog is None or self.dialog.update(self.controls):
            self.dialog = None
            self.mode = Mode.EXPLORE

    def _execute_command(self, command_id: str) -> None:
        if command_id == "attack":
            self.state.attack()
        elif command_id == "items":
            self.inventory_view.open()
            self.mode = Mode.INVENTORY
        elif command_id == "equipment":
            self.equipment_view.open()
            self.mode = Mode.EQUIPMENT
        elif command_id == "skills":
            self.skill_view.open(self.state.learned_skills())
            self.mode = Mode.SKILL_MENU
        elif command_id == "map":
            self.mode = Mode.FULL_MAP
        elif command_id == "cook":
            if self.state.can_cook:
                self.cutin.open()
                self.mode = Mode.COOKING_CUTIN
            else:
                self.state.log.add(self.state.cooking_unavailable_reason())
        else:
            self.state.log.add(f"「{command_label(command_id)}」は未実装です。")

    def _is_command_enabled(self, command_id: str) -> bool:
        return command_id != "cook" or self.state.can_cook

    def _confirm_descend(self) -> None:
        if not self.state.can_descend:
            self.state.log.add("これより下へは、まだ降りられない。")
            return
        self._confirm("階段を降りますか？", self.state.descend)

    # --- draw ---

    def draw(self) -> None:
        pyxel.cls(0)
        if self.mode == Mode.COOKING_CUTIN and self.cutin.shows_cutin:
            self.cutin.draw()
            return
        if self.mode == Mode.FULL_MAP:
            minimap.draw_full_map(
                self.state.floor, self.state.fog, self.state.player.pos, self._floor_label()
            )
            return
        if self.mode == Mode.LOG_HISTORY:
            self.log_history.draw()
            return

        player = self.state.player
        self._draw_map()
        self._draw_curse_flash()
        exp_next = exp_to_next_level(player.level, self.state.params.progression)
        hud.draw_status_bar(player, self._floor_label(), exp_next)
        self._draw_bottom_panel()
        self._draw_player_statuses()
        if self.banner_frames > 0:
            self._draw_floor_banner()
        if self.show_debug:
            self._draw_debug()

        if self.mode == Mode.INVENTORY:
            self.inventory_view.draw()
        elif self.mode == Mode.EQUIPMENT:
            self.equipment_view.draw()
        elif self.mode == Mode.SKILL_MENU:
            self.skill_view.draw(player.mp)
        elif self.mode == Mode.NOTEBOOK:
            self.notebook_view.draw()
        elif self.mode == Mode.CONFIRM and self.dialog is not None:
            self.dialog.draw()
        if self.mode == Mode.COOKING_CUTIN:
            self.cutin.draw_overlay()  # ワイプの途中（探索画面側）

    def _floor_label(self) -> str:
        return f"B{self.state.floor.number}F {self.state.area.name}"

    def _draw_map(self) -> None:
        ts = config.TILE_SIZE
        floor, fog, player = self.state.floor, self.state.fog, self.state.player
        view_w, view_h = config.MAP_VIEW_TILES_W, config.MAP_VIEW_TILES_H
        cam_x, cam_y = camera_origin(player.x, player.y, floor.width, floor.height, view_w, view_h)
        frame = pyxel.frame_count // config.ANIMATION_TICKS
        fire_frame = pyxel.frame_count // 5
        traps = {trap.pos: trap for trap in floor.traps if trap.discovered}

        shake_x, shake_y = self.effects.offset

        def screen_pos(x: int, y: int) -> tuple[int, int]:
            return (x - cam_x) * ts + shake_x, config.MAP_TOP + (y - cam_y) * ts + shake_y

        def visible(pos: tuple[int, int]) -> bool:
            return fog.state(*pos) == Visibility.VISIBLE

        pyxel.clip(0, config.MAP_TOP, config.SCREEN_WIDTH, config.MAP_VIEW_HEIGHT)
        # 既知タイルを暗いパレットで描いてから、視界内のタイルを通常の色で描く
        for visibility in (Visibility.KNOWN, Visibility.VISIBLE):
            if visibility == Visibility.KNOWN:
                for src, dst in KNOWN_TILE_PALETTE.items():
                    pyxel.pal(src, dst)
            for ty in range(view_h):
                for tx in range(view_w):
                    mx, my = cam_x + tx, cam_y + ty
                    if fog.state(mx, my) != visibility:
                        continue
                    tile = floor.tile_at(mx, my)
                    # 部屋や通路に接していない岩盤は描かず、黒のままにする
                    if tile == Tile.WALL and not floor.is_edge_wall(mx, my):
                        continue
                    sx, sy = screen_pos(mx, my)
                    self.sprites.draw(self._tile_sprite(tile, mx, my), sx, sy, frame, colkey=None)
                    trap = traps.get((mx, my))
                    if trap is not None:
                        self.sprites.draw(trap.definition.sprite, sx, sy)
                    if floor.campfire_at(mx, my) is not None:
                        self.sprites.draw(CAMPFIRE_SPRITE, sx, sy, fire_frame)
            pyxel.pal()

        # アイテム・宝箱・敵は視界内のものだけを描く（仕様書 5.4。ミミックと宝箱を見分けさせない）
        for floor_item in floor.items:
            if visible(floor_item.pos):
                self.sprites.draw(floor_item.item.definition.sprite, *screen_pos(*floor_item.pos))
        for chest in floor.chests:
            if visible(chest.pos):
                self.sprites.draw(chest.sprite_name, *screen_pos(*chest.pos))
        for monster in floor.monsters:
            if visible(monster.pos):
                sx, sy = screen_pos(*monster.pos)
                self.sprites.draw(monster.sprite_name, sx, sy, frame, offset=True)
                if self.effects.is_flashing(*monster.pos):
                    self.effects.draw_flash(sx, sy)
        px, py = screen_pos(player.x, player.y)
        self.sprites.draw(player.sprite_name, px, py, frame)
        if self.effects.is_flashing(player.x, player.y):
            self.effects.draw_flash(px, py)
        self.effects.draw(screen_pos)
        pyxel.clip()

    def _draw_curse_flash(self) -> None:
        """呪いの発動: マップを紫色に点滅させる（仕様書 14章）。"""
        if self.curse_flash_frames <= 0 or (self.curse_flash_frames // 4) % 2:
            return
        pyxel.dither(0.5)
        pyxel.rect(0, config.MAP_TOP, config.SCREEN_WIDTH, config.MAP_VIEW_HEIGHT, COLOR_CURSE)
        pyxel.dither(1.0)

    def _tile_sprite(self, tile: Tile, x: int, y: int) -> str:
        """エリア別の素材（例: wall_moss）があればそれを、なければ共通の素材を使う。"""
        if tile in (Tile.FLOOR, Tile.CORRIDOR) and self.state.floor.in_safe_zone(x, y):
            return SAFE_FLOOR_SPRITE  # 焚き火の周囲（安全地帯）の床
        base = SPRITE_NAMES[tile]
        area_specific = f"{base}_{self.state.area.id}"
        return area_specific if self.sprites.has(area_specific) else base

    def _draw_bottom_panel(self) -> None:
        top = config.MAP_TOP + config.MAP_VIEW_HEIGHT
        pyxel.line(0, top, config.SCREEN_WIDTH - 1, top, COLOR_FRAME)
        self.command_bar.draw(
            focused=self.mode == Mode.COMMAND_BAR, is_enabled=self._is_command_enabled
        )
        draw_recent(self.state.log, top + 15)

    def _draw_player_statuses(self) -> None:
        names = self.state.player_status_names()
        if not names:
            return
        text = " ".join(names)
        pyxel.rect(0, config.MAP_TOP, font.text_width(text) + 4, 10, 0)
        font.draw_text(2, config.MAP_TOP + 1, text, COLOR_STATUS)

    def _draw_floor_banner(self) -> None:
        label = self._floor_label()
        width = font.text_width(label)
        x = (config.SCREEN_WIDTH - width) // 2
        y = config.MAP_TOP + (config.MAP_VIEW_HEIGHT - config.TILE_SIZE) // 2
        pyxel.rect(x - 6, y - 4, width + 12, 16, 0)
        pyxel.rectb(x - 6, y - 4, width + 12, 16, COLOR_SUBTEXT)
        font.draw_text(x, y, label, COLOR_TEXT)

    def _draw_debug(self) -> None:
        s = self.state
        text = f"SEED {s.run_seed} TURN {s.turn} POS {s.player.x},{s.player.y}"
        width = font.text_width(text)
        x = config.SCREEN_WIDTH - width - 2
        pyxel.rect(x - 2, config.MAP_TOP, width + 4, 10, 0)
        font.draw_text(x, config.MAP_TOP + 1, text, COLOR_DEBUG)
