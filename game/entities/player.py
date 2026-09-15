"""プレイヤー（レオ）。仕様書 6章。

pyxel を import しないこと。
"""

from __future__ import annotations

from dataclasses import dataclass

from game.entities.entity import Entity
from game.world.direction import FACINGS

PLAYER_NAME = "レオ"
PLAYER_SPRITE_BASE = "leo"
PLAYER_SPRITE_NAMES: tuple[str, ...] = tuple(f"{PLAYER_SPRITE_BASE}_{f}" for f in FACINGS)


@dataclass
class Player(Entity):
    name: str = PLAYER_NAME

    @property
    def sprite_name(self) -> str:
        return f"{PLAYER_SPRITE_BASE}_{self.facing.sprite_facing}"
