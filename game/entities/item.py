"""アイテムの定義と個体。仕様書 10章 / 11章。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import DataValidationError

GOLD_ID = "gold"

CATEGORY_HERB = "herb"
CATEGORY_FOOD = "food"
CATEGORY_SCROLL = "scroll"
CATEGORY_TOOL = "tool"
CATEGORY_AMMO = "ammo"
CATEGORY_MEMO = "memo"
CATEGORY_GOLD = "gold"
CATEGORY_WEAPON = "weapon"


@dataclass(frozen=True)
class Effect:
    """使ったときの効果。type ごとの処理は systems/game_state.py にある。"""

    type: str
    value: int = 0
    statuses: tuple[str, ...] = ()
    radius: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Effect:
        return cls(
            type=str(data["type"]),
            value=int(data.get("value", 0)),
            statuses=tuple(str(s) for s in data.get("statuses", ())),
            radius=int(data.get("radius", 0)),
        )


@dataclass(frozen=True)
class WeaponStats:
    attack: int
    reach: str
    length: int = 1
    crit_rate: int | None = None  # None なら基本のクリティカル率
    ingredient_drop_multiplier: float = 1.0
    pull_item_range: int = 0
    uses_arrows: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WeaponStats:
        crit_rate = data.get("crit_rate")
        return cls(
            attack=int(data["attack"]),
            reach=str(data["reach"]),
            length=int(data.get("length", 1)),
            crit_rate=None if crit_rate is None else int(crit_rate),
            ingredient_drop_multiplier=float(data.get("ingredient_drop_multiplier", 1.0)),
            pull_item_range=int(data.get("pull_item_range", 0)),
            uses_arrows=bool(data.get("uses_arrows", False)),
        )


@dataclass(frozen=True)
class ItemDef:
    id: str
    name: str
    category: str
    sprite: str
    description: str
    price: int | None = None
    spawn_weight: int = 0
    stackable: bool = False
    spawn_count: tuple[int, int] = (1, 1)
    effects: tuple[Effect, ...] = ()
    weapon: WeaponStats | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], source: str) -> ItemDef:
        required = ("id", "name", "category", "sprite", "description")
        missing = [key for key in required if key not in data]
        if missing:
            raise DataValidationError(
                f"{source}: {data.get('id', '?')}: 必須キーがありません: {', '.join(missing)}"
            )
        low, high = data.get("spawn_count", (1, 1))
        price = data.get("price")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            category=str(data["category"]),
            sprite=str(data["sprite"]),
            description=str(data["description"]),
            price=None if price is None else int(price),
            spawn_weight=int(data.get("spawn_weight", 0)),
            stackable=bool(data.get("stackable", False)),
            spawn_count=(int(low), int(high)),
            effects=tuple(Effect.from_dict(e) for e in data.get("effects", ())),
            weapon=WeaponStats.from_dict(data) if data["category"] == CATEGORY_WEAPON else None,
        )

    @property
    def use_label(self) -> str | None:
        """アイテムメニューでの「使う」の表記。使えないアイテムは None。"""
        if not self.effects:
            return None
        if self.category == CATEGORY_FOOD:
            return "食べる"
        if self.category in (CATEGORY_SCROLL, CATEGORY_MEMO):
            return "読む"
        return "使う"


@dataclass(eq=False)
class ItemInstance:
    definition: ItemDef
    count: int = 1

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        if self.definition.stackable:
            return f"{self.definition.name}（{self.count}本）"
        return self.definition.name


@dataclass(eq=False)
class FloorItem:
    """床に落ちているアイテム。"""

    item: ItemInstance
    x: int
    y: int

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)
