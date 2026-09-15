"""1回の挑戦（ラン）中のゲーム状態と、プレイヤーの行動によるターン進行。

描画や入力から切り離し、テストから直接操作できるようにしている。
pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game import rng
from game.entities.player import Player, PlayerParams
from game.systems import progression
from game.systems.message_log import MessageLog
from game.systems.progression import ProgressionParams, SurvivalParams
from game.systems.turn import TurnScheduler
from game.world.direction import Direction
from game.world.floor import Area, Floor, area_for_floor
from game.world.fov import FogMap, FovParams, compute_visible
from game.world.mapgen import MapGenParams, generate_floor
from game.world.tiles import Tile


@dataclass(frozen=True)
class GameParams:
    """data/ から読み込んだ、ラン全体で使うパラメータ。"""

    mapgen: MapGenParams
    player: PlayerParams
    survival: SurvivalParams
    progression: ProgressionParams
    fov: FovParams
    inventory_capacity: int
    areas: tuple[Area, ...]

    @classmethod
    def from_data(cls, data: Mapping[str, Mapping[str, Any]]) -> GameParams:
        balance = data["balance"]
        return cls(
            mapgen=MapGenParams.from_dict(balance["mapgen"]),
            player=PlayerParams.from_dict(balance["player"]),
            survival=SurvivalParams.from_dict(balance["survival"]),
            progression=ProgressionParams.from_dict(balance["progression"]),
            fov=FovParams.from_dict(balance["fov"]),
            inventory_capacity=int(balance["inventory"]["capacity"]),
            areas=tuple(Area.from_dict(area) for area in data["floors"]["areas"]),
        )

    @property
    def last_floor(self) -> int:
        return max(area.last_floor for area in self.areas)


class GameState:
    def __init__(self, run_seed: int, params: GameParams) -> None:
        self.run_seed = run_seed
        self.params = params
        self.player = Player.from_params(params.player)
        self.scheduler = TurnScheduler()
        self.log = MessageLog()
        self.floor: Floor
        self.area: Area
        self.fog: FogMap
        self.enter_floor(1)
        self.log.add(f"{self.player.name}は迷宮の奥へ足を踏み入れた。")

    # --- 状態の参照 ---

    @property
    def turn(self) -> int:
        return self.scheduler.turn

    @property
    def is_game_over(self) -> bool:
        return self.player.hp <= 0

    @property
    def player_on_stairs(self) -> bool:
        return self.floor.tile_at(*self.player.pos) == Tile.STAIRS_DOWN

    @property
    def can_descend(self) -> bool:
        # B20F（ボス階）はフェーズ7で固定レイアウトにし、階段を置かない
        return self.player_on_stairs and self.floor.number < self.params.last_floor

    @property
    def can_cook(self) -> bool:
        # 焚き火と携帯コンロはフェーズ5で実装する
        return False

    # --- 階層 ---

    def enter_floor(self, number: int) -> None:
        self.floor = generate_floor(
            rng.floor_rng(self.run_seed, number), number, self.params.mapgen
        )
        self.area = area_for_floor(self.params.areas, number)
        self.fog = FogMap(self.floor.width, self.floor.height)
        self.player.x, self.player.y = self.floor.start
        self.update_fov()

    def update_fov(self) -> None:
        p = self.player
        self.fog.update(compute_visible(self.floor, p.x, p.y, p.facing, self.params.fov))

    # --- プレイヤーの行動 ---

    def move_player(self, direction: Direction) -> bool:
        """移動できたら1ターン経過する。壁に向かった場合は向きだけ変わり、ターンは進まない。"""
        if self.is_game_over:
            return False
        moved = self.player.try_move(self.floor, direction)
        if moved:
            self._end_player_action()
        else:
            self.update_fov()
        return moved

    def face(self, direction: Direction) -> None:
        """向きだけを変える（ターンは進まない）。"""
        self.player.facing = direction
        self.update_fov()

    def wait(self) -> None:
        """足踏みして1ターン経過させる。罠の探索はフェーズ3で実装する。"""
        if self.is_game_over:
            return
        self._end_player_action()

    def descend(self) -> bool:
        """下り階段の上にいれば次の階へ進む（ターンは進まない）。"""
        if not self.can_descend:
            return False
        self.enter_floor(self.floor.number + 1)
        progression.recover_mp_on_descend(self.player, self.params.survival)
        self.log.add(f"{self.player.name}は B{self.floor.number}F へ降りた。")
        return True

    # --- ターン進行 ---

    def _end_player_action(self) -> None:
        self.scheduler.after_player_action(
            self.player,
            monsters=[],
            act=lambda _monster: None,
            end_turn=self._on_turn_end,
            stop=lambda: self.is_game_over,
        )
        self.update_fov()

    def _on_turn_end(self, turn: int) -> None:
        for message in progression.apply_turn_end(self.player, turn, self.params.survival):
            self.log.add(message)
        if self.is_game_over:
            self.log.add(f"{self.player.name}は力尽きた……")
