"""迷宮の行商人。仕様書 12.4。

拠点の施設（systems/meta.py）と違い、支払いは**迷宮の中で拾った所持金**で行う。
死ねば所持金ごと失うので、ここで使うかどうかがそのまま賭けになる。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping

from game.entities.item import ItemDef, ItemInstance
from game.entities.player import Player
from game.systems.inventory import Inventory
from game.systems.spawn import SpawnParams
from game.systems.status import AILMENT, StatusDef

# 行商人が扱う品。拠点の道具屋と同じく、値段の付いたものだけを売る
SERVICE_BUY = "buy"
SERVICE_UNCURSE = "uncurse"
SERVICE_CURE = "cure"


def price_of(definition: ItemDef, params: SpawnParams) -> int:
    """迷宮での売値。拠点より割高にする（運び賃）。"""
    base = definition.price or 0
    return int(base * params.merchant_price_ratio)


def stock(items: Mapping[str, ItemDef], params: SpawnParams) -> list[ItemDef]:
    """品揃え。消耗品だけを扱い、装備は置かない（迷宮では担げないため）。"""
    sellable = [i for i in items.values() if i.price is not None and i.category in CONSUMABLES]
    return sorted(sellable, key=lambda i: price_of(i, params))


CONSUMABLES = ("herb", "food", "scroll", "tool", "ammo")


def buy(player: Player, inventory: Inventory, definition: ItemDef, params: SpawnParams) -> str:
    """消耗品を1つ買う。まとめ売りはしない（拠点の bundles は使わない）。"""
    price = price_of(definition, params)
    if player.gold < price:
        return "お金が足りない。"
    item = ItemInstance(definition, 1)
    if not inventory.can_add(item):
        return "これ以上は持てない。"
    inventory.add(item)
    player.gold -= price
    return f"{item.name}を{price}Gで買った。"


def uncurse(player: Player, item: ItemInstance, params: SpawnParams) -> str:
    """呪いを解く。装備したまま解けるので、外せなくなった装備を救える。"""
    if not item.cursed:
        item.curse_known = True
        return f"{item.name}は呪われていない。"
    if player.gold < params.merchant_uncurse_cost:
        return "お金が足りない。"
    player.gold -= params.merchant_uncurse_cost
    item.curse = None
    item.curse_known = True
    return f"{item.name}の呪いが解けた。"


def ailments(player: Player, statuses: Mapping[str, StatusDef]) -> list[StatusDef]:
    """いま治せる状態異常（バフは対象外）。"""
    return [
        statuses[status_id]
        for status_id in player.statuses.active_ids()
        if status_id in statuses and statuses[status_id].kind == AILMENT
    ]


def cure(player: Player, statuses: Mapping[str, StatusDef], params: SpawnParams) -> str:
    """毒などの状態異常をまとめて治す。最大HP減少で減った分も戻す。"""
    targets = ailments(player, statuses)
    if not targets:
        return "治すものがない。"
    if player.gold < params.merchant_cure_cost:
        return "お金が足りない。"
    player.gold -= params.merchant_cure_cost
    names: list[str] = []
    for definition in targets:
        stacks = player.statuses.stacks(definition.id)
        if not player.statuses.remove(definition.id):
            continue
        names.append(definition.name)
        if definition.id == "max_hp_down":
            player.max_hp += stacks * definition.value
    return f"{'・'.join(names)}が治った。"
