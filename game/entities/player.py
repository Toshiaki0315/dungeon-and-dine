"""プレイヤー（レオ）。仕様書 6章。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import dataclass_from_dict
from game.entities.entity import Entity
from game.world.direction import FACINGS

PLAYER_NAME = "レオ"
PLAYER_SPRITE_BASE = "leo"
PLAYER_SPRITE_NAMES: tuple[str, ...] = tuple(f"{PLAYER_SPRITE_BASE}_{f}" for f in FACINGS)


@dataclass(frozen=True)
class PlayerParams:
    """初期ステータス。balance.json の "player" で定義する。"""

    level: int
    hp: int
    mp: int
    atk: int
    defense: int
    hit: int
    evade: int
    satiety: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PlayerParams:
        return dataclass_from_dict(cls, data, "player")


@dataclass
class Player(Entity):
    name: str = PLAYER_NAME
    level: int = 1
    exp: int = 0
    gold: int = 0
    hp: int = 1
    max_hp: int = 1
    mp: int = 0
    max_mp: int = 0
    atk: int = 0
    defense: int = 0
    hit: int = 0
    evade: int = 0
    satiety: int = 0
    max_satiety: int = 0
    satiety_progress: int = 0  # 満腹度が1減るまでの蓄積（% 単位）

    @classmethod
    def from_params(cls, params: PlayerParams, x: int = 0, y: int = 0) -> Player:
        return cls(
            x=x,
            y=y,
            level=params.level,
            hp=params.hp,
            max_hp=params.hp,
            mp=params.mp,
            max_mp=params.mp,
            atk=params.atk,
            defense=params.defense,
            hit=params.hit,
            evade=params.evade,
            satiety=params.satiety,
            max_satiety=params.satiety,
        )

    @property
    def sprite_name(self) -> str:
        return f"{PLAYER_SPRITE_BASE}_{self.facing.sprite_facing}"
