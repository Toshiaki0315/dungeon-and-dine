"""拠点（ベースキャンプ）のデータと施設の処理。仕様書 12.3。

死亡しても残るデータ（レシピ手帳・拠点資金・倉庫・拡張・実績）をまとめて持つ。
pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from game.data_loader import DataValidationError, dataclass_from_dict
from game.entities.item import SLOTS, ItemDef, ItemInstance
from game.entities.player import DEFAULT_APPEARANCE, PLAYER_NAME
from game.systems.cooking import Notebook
from game.systems.inventory import Inventory


@dataclass(frozen=True)
class Expansion:
    """拡張1回あたりの値段と増える枠数、購入できる回数。"""

    cost: int
    amount: int
    max_times: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], section: str) -> Expansion:
        return dataclass_from_dict(cls, data, section)


@dataclass(frozen=True)
class BaseCampParams:
    """拠点のパラメータ。balance.json の "base_camp" で定義する。"""

    storage_capacity: int
    appraise_cost: int
    uncurse_cost: int
    inventory_expansion: Expansion
    storage_expansion: Expansion
    bundles: Mapping[str, int]  # 道具屋でまとめ売りする個数（矢など）

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BaseCampParams:
        required = (
            "storage_capacity", "appraise_cost", "uncurse_cost",
            "inventory_expansion", "storage_expansion", "bundles",
        )  # fmt: skip
        missing = [key for key in required if key not in data]
        if missing:
            raise DataValidationError(f"base_camp: 必須キーがありません: {', '.join(missing)}")
        return cls(
            storage_capacity=int(data["storage_capacity"]),
            appraise_cost=int(data["appraise_cost"]),
            uncurse_cost=int(data["uncurse_cost"]),
            inventory_expansion=Expansion.from_dict(
                data["inventory_expansion"], "base_camp.inventory_expansion"
            ),
            storage_expansion=Expansion.from_dict(
                data["storage_expansion"], "base_camp.storage_expansion"
            ),
            bundles={str(k): int(v) for k, v in data["bundles"].items()},
        )


@dataclass
class Loadout:
    """拠点に置いてある持ち物と装備。次の挑戦にそのまま持って行く。"""

    items: Inventory
    equipment: dict[str, ItemInstance | None] = field(default_factory=lambda: dict.fromkeys(SLOTS))

    def is_equipped(self, item: ItemInstance) -> bool:
        return any(equipped is item for equipped in self.equipment.values())

    def clear(self) -> None:
        self.items.items = []
        self.equipment = dict.fromkeys(SLOTS)


RANKING_SIZE = 10  # ランキングに並べる件数
SCORE_CAPACITY = 50  # 保存しておく記録の数（古いものから捨てる）
NAME_MAX_LENGTH = 10  # 主人公の名前の長さ（仕様書 6.1）

OUTCOME_CLEAR = "clear"
OUTCOME_RETURN = "return"
OUTCOME_DEATH = "death"
OUTCOME_LABELS = {OUTCOME_CLEAR: "クリア", OUTCOME_RETURN: "生還", OUTCOME_DEATH: "力尽きた"}


@dataclass(frozen=True)
class ScoreEntry:
    """1回の挑戦の記録（ランキング用）。"""

    name: str
    floor: int
    gold: int
    turn: int
    outcome: str

    @property
    def outcome_label(self) -> str:
        return OUTCOME_LABELS.get(self.outcome, self.outcome)


def ranking_by_floor(scores: list[ScoreEntry], size: int = RANKING_SIZE) -> list[ScoreEntry]:
    """到達した階層の深い順。同じ階層なら、ターン数が少ないほうを上にする。"""
    return sorted(scores, key=lambda s: (-s.floor, s.turn))[:size]


def ranking_by_gold(scores: list[ScoreEntry], size: int = RANKING_SIZE) -> list[ScoreEntry]:
    """獲得した所持金の多い順。"""
    return sorted(scores, key=lambda s: (-s.gold, s.turn))[:size]


@dataclass
class MetaProgress:
    """死亡しても残るデータ（仕様書 12.3）。meta.json に保存する。"""

    loadout: Loadout
    storage: Inventory
    notebook: Notebook = field(default_factory=Notebook)
    funds: int = 0  # 拠点資金
    inventory_expansions: int = 0
    storage_expansions: int = 0
    clears: int = 0
    deepest_floor: int = 1
    player_name: str = PLAYER_NAME
    appearance: str = DEFAULT_APPEARANCE  # 主人公の見た目（APPEARANCES の ID）
    scores: list[ScoreEntry] = field(default_factory=list)

    @classmethod
    def new(cls, inventory_capacity: int, stack_max: int, params: BaseCampParams) -> MetaProgress:
        return cls(
            loadout=Loadout(Inventory(inventory_capacity, stack_max)),
            storage=Inventory(params.storage_capacity, stack_max),
        )

    def record_run(self, floor_number: int) -> None:
        self.deepest_floor = max(self.deepest_floor, floor_number)

    def record_score(self, entry: ScoreEntry) -> None:
        """ランキング用に、1回の挑戦の結果を残す（仕様書 6.6）。"""
        self.scores.append(entry)
        del self.scores[:-SCORE_CAPACITY]

    def finish_run(
        self,
        *,
        survived: bool,
        items: list[ItemInstance],
        equipment: Mapping[str, ItemInstance | None],
        gold: int,
        floor_number: int,
        turn: int = 0,
        cleared: bool = False,
    ) -> None:
        """挑戦の終わりに引き継ぎを行い、ランキングに記録する（仕様書 6.6 / 12.3）。

        生還: 所持品と装備をそのまま持ち帰り、所持金は拠点資金に加える（呪いは残る）。
        死亡: 所持品・装備・所持金を失う。
        """
        outcome = OUTCOME_CLEAR if cleared else OUTCOME_RETURN if survived else OUTCOME_DEATH
        self.record_score(ScoreEntry(self.player_name, floor_number, gold, turn, outcome))
        self.record_run(floor_number)
        if not survived:
            self.loadout.clear()
            return
        self.funds += gold
        self.loadout.items.items = list(items)
        self.loadout.equipment = dict(equipment)


# --- 施設（結果はログに出すメッセージで返す） ---


def shop_items(items: Mapping[str, ItemDef]) -> list[ItemDef]:
    """道具屋の品揃え。価格が決まっているアイテムを売る（装備は修正値+0・鑑定済み）。"""
    return [item for item in items.values() if item.price is not None]


def buy(meta: MetaProgress, params: BaseCampParams, definition: ItemDef) -> str:
    price = definition.price
    if price is None:
        return f"{definition.name}は売り物ではない。"
    if meta.funds < price:
        return "お金が足りない。"
    item = ItemInstance(definition, params.bundles.get(definition.id, 1))
    if not meta.loadout.items.can_add(item):
        return "これ以上は持てない。倉庫に預けるか、枠を拡張しよう。"
    meta.loadout.items.add(item)
    meta.funds -= price
    return f"{item.name}を{price}Gで買った。"


def appraise(meta: MetaProgress, params: BaseCampParams, item: ItemInstance) -> str:
    if item.identified:
        return f"{item.name}はもう鑑定されている。"
    if meta.funds < params.appraise_cost:
        return "お金が足りない。"
    meta.funds -= params.appraise_cost
    item.identified = True
    item.curse_known = True
    suffix = " 呪われている！" if item.cursed else ""
    return f"{item.name}だった。{suffix}"


def uncurse(meta: MetaProgress, params: BaseCampParams, item: ItemInstance) -> str:
    if not item.cursed:
        return f"{item.name}は呪われていない。"
    if meta.funds < params.uncurse_cost:
        return "お金が足りない。"
    meta.funds -= params.uncurse_cost
    item.curse = None
    item.curse_known = True
    for slot, equipped in meta.loadout.equipment.items():
        if equipped is item:
            meta.loadout.equipment[slot] = None  # 解呪して外す
    return f"{item.name}の呪いが解けた。"


def deposit(meta: MetaProgress, item: ItemInstance) -> str:
    """倉庫に預ける。装備中のものは外してから預ける。"""
    if item not in meta.loadout.items.items:
        return "それは持っていない。"
    if not meta.storage.can_add(item):
        return "倉庫がいっぱいだ。"
    if meta.loadout.is_equipped(item):
        if item.cursed:
            return f"{item.name}は呪われていて外せない。"
        for slot, equipped in meta.loadout.equipment.items():
            if equipped is item:
                meta.loadout.equipment[slot] = None
    meta.loadout.items.remove(item)
    meta.storage.add(item)
    return f"{item.name}を倉庫に預けた。"


def withdraw(meta: MetaProgress, item: ItemInstance) -> str:
    if item not in meta.storage.items:
        return "倉庫にない。"
    if not meta.loadout.items.can_add(item):
        return "これ以上は持てない。"
    meta.storage.remove(item)
    meta.loadout.items.add(item)
    return f"{item.name}を引き出した。"


def expand_inventory(meta: MetaProgress, params: BaseCampParams) -> str:
    expansion = params.inventory_expansion
    if meta.inventory_expansions >= expansion.max_times:
        return "これ以上は広げられない。"
    if meta.funds < expansion.cost:
        return "お金が足りない。"
    meta.funds -= expansion.cost
    meta.inventory_expansions += 1
    meta.loadout.items.capacity += expansion.amount
    return f"持ち物の枠が{expansion.amount}増えた。"


def expand_storage(meta: MetaProgress, params: BaseCampParams) -> str:
    expansion = params.storage_expansion
    if meta.storage_expansions >= expansion.max_times:
        return "これ以上は広げられない。"
    if meta.funds < expansion.cost:
        return "お金が足りない。"
    meta.funds -= expansion.cost
    meta.storage_expansions += 1
    meta.storage.capacity += expansion.amount
    return f"倉庫の枠が{expansion.amount}増えた。"
