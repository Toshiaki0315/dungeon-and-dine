"""プレイヤー（主人公）。仕様書 6章。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from game.data_loader import dataclass_from_dict
from game.entities.entity import Entity
from game.entities.item import SLOT_WEAPON, SLOTS, ItemInstance
from game.world.direction import FACINGS

PLAYER_NAME = "レオ"
# 主人公の見た目（仕様書 6.1）。(ID, 表示名)。見た目だけの違いで、能力は変わらない
APPEARANCES: tuple[tuple[str, str], ...] = (
    ("warrior", "戦士"),
    ("fighter", "格闘家"),
    ("mage", "魔法使い"),
    ("priest", "僧侶"),
    ("merchant", "商人"),
)
APPEARANCE_IDS: tuple[str, ...] = tuple(appearance for appearance, _ in APPEARANCES)
DEFAULT_APPEARANCE = "warrior"
PLAYER_SPRITE_BASE = "hero"


def player_sprite_name(appearance: str, facing: str) -> str:
    """見た目と向きから素材名を作る（例: hero_mage_left）。"""
    return f"{PLAYER_SPRITE_BASE}_{appearance}_{facing}"


def normalize_appearance(value: object) -> str:
    """知らない見た目（古いセーブデータなど）は既定の見た目にする。"""
    return value if isinstance(value, str) and value in APPEARANCE_IDS else DEFAULT_APPEARANCE


PLAYER_SPRITE_NAMES: tuple[str, ...] = tuple(
    player_sprite_name(appearance, facing) for appearance in APPEARANCE_IDS for facing in FACINGS
)


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


def _empty_equipment() -> dict[str, ItemInstance | None]:
    return dict.fromkeys(SLOTS)


@dataclass
class Player(Entity):
    name: str = PLAYER_NAME
    appearance: str = DEFAULT_APPEARANCE
    level: int = 1
    exp: int = 0
    gold: int = 0
    hp: int = 1
    max_hp: int = 1  # 鎧のボーナスと最大HP減少を反映した値
    mp: int = 0
    max_mp: int = 0
    atk: int = 0
    defense: int = 0
    hit: int = 0
    evade: int = 0
    satiety: int = 0
    max_satiety: int = 0
    satiety_progress: int = 0  # 満腹度が1減るまでの蓄積（% 単位）
    equipment: dict[str, ItemInstance | None] = field(default_factory=_empty_equipment)
    skills: list[str] = field(default_factory=list)

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
    def weapon(self) -> ItemInstance | None:
        return self.equipment[SLOT_WEAPON]

    @property
    def sprite_name(self) -> str:
        return player_sprite_name(self.appearance, self.facing.sprite_facing)

    def is_equipped(self, item: ItemInstance) -> bool:
        return any(equipped is item for equipped in self.equipment.values())

    def equipped_items(self) -> list[ItemInstance]:
        return [item for item in self.equipment.values() if item is not None]
