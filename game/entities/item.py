"""アイテムの定義と個体、宝箱。仕様書 10章 / 11章 / 12.2。

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
CATEGORY_ARMOR = "armor"

SLOT_WEAPON = "weapon"
SLOT_SHIELD = "shield"
SLOT_HELMET = "helmet"
SLOT_ARMOR = "armor"
SLOT_SHOES = "shoes"
SLOTS: tuple[str, ...] = (SLOT_WEAPON, SLOT_SHIELD, SLOT_HELMET, SLOT_ARMOR, SLOT_SHOES)
SLOT_NAMES: dict[str, str] = {
    SLOT_WEAPON: "武器",
    SLOT_SHIELD: "盾",
    SLOT_HELMET: "兜",
    SLOT_ARMOR: "鎧",
    SLOT_SHOES: "靴",
}

CHEST_CLOSED_SPRITE = "chest_closed"
CHEST_OPEN_SPRITE = "chest_open"


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
class ArmorStats:
    slot: str
    defense: int
    block_rate: int = 0  # 盾: ダメージを0にする確率（%）
    sight_bonus: int = 0  # 兜: 通路での視界
    status_resist: bool = False  # 兜: 状態異常にかかる確率を半減
    max_hp_bonus: int = 0  # 鎧
    trap_find_bonus: int = 0  # 靴: 罠の発見率（%）
    trap_avoid_rate: int = 0  # 靴: 罠を踏んでも発動しない確率（%）
    hunger_rate_percent: int = 100  # 靴: 満腹度の減る速さ

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ArmorStats:
        if data.get("slot") not in SLOTS[1:]:
            raise DataValidationError(f"armors.json: {data.get('id', '?')}: slot が不正です")
        return cls(
            slot=str(data["slot"]),
            defense=int(data["defense"]),
            block_rate=int(data.get("block_rate", 0)),
            sight_bonus=int(data.get("sight_bonus", 0)),
            status_resist=bool(data.get("status_resist", False)),
            max_hp_bonus=int(data.get("max_hp_bonus", 0)),
            trap_find_bonus=int(data.get("trap_find_bonus", 0)),
            trap_avoid_rate=int(data.get("trap_avoid_rate", 0)),
            hunger_rate_percent=int(data.get("hunger_rate_percent", 100)),
        )


@dataclass(frozen=True)
class EquipmentTrait:
    """装備の印（良い効果）や呪い（悪い効果）。balance.json の "equipment" で定義する。"""

    id: str
    name: str
    crit_bonus: int = 0
    hit_percent: int = 100
    hunger_rate_percent: int = 100
    sight_bonus: int = 0
    cook_fail_bonus: int = 0
    fire: bool = False
    sturdy: bool = False
    skill_seal: bool = False
    no_trap_find: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EquipmentTrait:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            crit_bonus=int(data.get("crit_bonus", 0)),
            hit_percent=int(data.get("hit_percent", 100)),
            hunger_rate_percent=int(data.get("hunger_rate_percent", 100)),
            sight_bonus=int(data.get("sight_bonus", 0)),
            cook_fail_bonus=int(data.get("cook_fail_bonus", 0)),
            fire=bool(data.get("fire", False)),
            sturdy=bool(data.get("sturdy", False)),
            skill_seal=bool(data.get("skill_seal", False)),
            no_trap_find=bool(data.get("no_trap_find", False)),
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
    armor: ArmorStats | None = None

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
        category = data["category"]
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            category=str(category),
            sprite=str(data["sprite"]),
            description=str(data["description"]),
            price=None if price is None else int(price),
            spawn_weight=int(data.get("spawn_weight", 0)),
            stackable=bool(data.get("stackable", False)),
            spawn_count=(int(low), int(high)),
            effects=tuple(Effect.from_dict(e) for e in data.get("effects", ())),
            weapon=WeaponStats.from_dict(data) if category == CATEGORY_WEAPON else None,
            armor=ArmorStats.from_dict(data) if category == CATEGORY_ARMOR else None,
        )

    @property
    def slot(self) -> str | None:
        if self.weapon is not None:
            return SLOT_WEAPON
        return self.armor.slot if self.armor is not None else None

    @property
    def is_equipment(self) -> bool:
        return self.slot is not None

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
    modifier: int = 0  # 装備の修正値（攻撃力または防御力に加算）
    mark: EquipmentTrait | None = None
    curse: EquipmentTrait | None = None
    identified: bool = True  # 修正値・印・呪いまで判明しているか（個体ごと）
    curse_known: bool = True  # 呪いの有無だけでも判明しているか

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def is_equipment(self) -> bool:
        return self.definition.is_equipment

    @property
    def cursed(self) -> bool:
        return self.curse is not None

    @property
    def name(self) -> str:
        definition = self.definition
        if definition.stackable:
            return f"{definition.name}（{self.count}本）"
        if not definition.is_equipment:
            return definition.name
        if not self.identified:
            return f"？の{definition.name}"
        name = f"{definition.name}{self.modifier:+d}" if self.modifier else definition.name
        return f"{name}〔{self.mark.name}〕" if self.mark is not None else name


@dataclass(eq=False)
class FloorItem:
    """床に落ちているアイテム。"""

    item: ItemInstance
    x: int
    y: int

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass(eq=False)
class Chest:
    """宝箱。調べると開き、中身が手に入る（1ターン消費）。開けたあとも通れない。"""

    contents: ItemInstance
    x: int
    y: int
    trapped: bool = False
    opened: bool = False

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def sprite_name(self) -> str:
        return CHEST_OPEN_SPRITE if self.opened else CHEST_CLOSED_SPRITE
