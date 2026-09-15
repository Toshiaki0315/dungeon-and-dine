"""敵・アイテム・罠の配置。仕様書 5.3 / 11.3。

pyxel を import しないこと。
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from game.data_loader import dataclass_from_dict
from game.entities.item import GOLD_ID, FloorItem, ItemInstance
from game.entities.monster import Monster
from game.systems.combat import round_half_up
from game.systems.traps import Trap
from game.world.floor import Floor
from game.world.tiles import Tile

if TYPE_CHECKING:
    from game.systems.catalog import Catalog

Position = tuple[int, int]


@dataclass(frozen=True)
class SpawnParams:
    """配置のパラメータ。balance.json の "spawn" で定義する。"""

    monsters_min: int
    monsters_max: int
    items_min: int
    items_max: int
    traps_min: int
    traps_max: int
    gold_min: int
    gold_max: int
    gold_per_floor_ratio: float  # 階層係数 = 1 + ratio × (階層 - 1)
    respawn_interval: int
    monster_gold_drop_chance: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SpawnParams:
        return dataclass_from_dict(cls, data, "spawn")


def weighted_choice(rng: random.Random, weights: Mapping[str, int]) -> str | None:
    total = sum(w for w in weights.values() if w > 0)
    if total <= 0:
        return None
    roll = rng.randrange(total)
    for key, weight in weights.items():
        if weight <= 0:
            continue
        if roll < weight:
            return key
        roll -= weight
    return None


def gold_amount(rng: random.Random, floor_number: int, params: SpawnParams) -> int:
    factor = 1 + params.gold_per_floor_ratio * (floor_number - 1)
    return round_half_up(rng.randint(params.gold_min, params.gold_max) * factor)


def populate_floor(
    floor: Floor,
    rng: random.Random,
    catalog: Catalog,
    params: SpawnParams,
    next_uid: Callable[[], int],
) -> None:
    """生成したばかりの階に、敵・床アイテム・罠を置く。"""
    start_room = floor.room_at(*floor.start)
    walkable = [
        (x, y) for y in range(floor.height) for x in range(floor.width) if floor.is_walkable(x, y)
    ]
    room_cells = [
        cell
        for room in floor.rooms
        for cell in room.cells()
        if floor.tile_at(*cell) == Tile.FLOOR and cell != floor.start
    ]

    # 敵はプレイヤーのいる部屋には置かない
    monster_cells = [
        c
        for c in walkable
        if c != floor.start and (start_room is None or not start_room.contains(*c))
    ]
    for _ in range(rng.randint(params.monsters_min, params.monsters_max)):
        cell = _pick_free(rng, monster_cells, lambda c: floor.monster_at(*c) is None)
        if cell is None:
            break
        spawn_monster(floor, rng, catalog, cell, next_uid)

    for _ in range(rng.randint(params.items_min, params.items_max)):
        cell = _pick_free(rng, room_cells, lambda c: floor.item_at(*c) is None)
        if cell is None:
            break
        floor.items.append(FloorItem(random_item(rng, catalog, floor.number, params), *cell))

    for _ in range(rng.randint(params.traps_min, params.traps_max)):
        cell = _pick_free(
            rng, room_cells, lambda c: floor.item_at(*c) is None and floor.trap_at(*c) is None
        )
        trap_id = weighted_choice(rng, {t.id: t.spawn_weight for t in catalog.traps.values()})
        if cell is None or trap_id is None:
            break
        floor.traps.append(Trap(catalog.traps[trap_id], *cell))


def spawn_monster(
    floor: Floor,
    rng: random.Random,
    catalog: Catalog,
    cell: Position,
    next_uid: Callable[[], int],
) -> Monster | None:
    monster_id = weighted_choice(rng, catalog.spawn_table(floor.number))
    if monster_id is None:
        return None
    monster = Monster.spawn(catalog.monsters[monster_id], *cell, next_uid())
    floor.monsters.append(monster)
    return monster


def respawn_monster(
    floor: Floor,
    rng: random.Random,
    catalog: Catalog,
    is_allowed: Callable[[Position], bool],
    next_uid: Callable[[], int],
) -> Monster | None:
    """is_allowed を満たす空きマス（視界外など）に1体出現させる。"""
    cells = [
        (x, y)
        for y in range(floor.height)
        for x in range(floor.width)
        if floor.is_walkable(x, y) and floor.monster_at(x, y) is None and is_allowed((x, y))
    ]
    if not cells:
        return None
    return spawn_monster(floor, rng, catalog, rng.choice(cells), next_uid)


def random_item(
    rng: random.Random, catalog: Catalog, floor_number: int, params: SpawnParams
) -> ItemInstance:
    """床に置くアイテムを1つ選ぶ。装備品の配置はフェーズ4で追加する。"""
    weights = {i.id: i.spawn_weight for i in catalog.items.values() if i.weapon is None}
    item_id = weighted_choice(rng, weights)
    assert item_id is not None, "items.json に spawn_weight が正のアイテムがありません"
    definition = catalog.items[item_id]
    if item_id == GOLD_ID:
        return ItemInstance(definition, gold_amount(rng, floor_number, params))
    if definition.stackable:
        return ItemInstance(definition, rng.randint(*definition.spawn_count))
    return ItemInstance(definition)


def _pick_free(
    rng: random.Random, cells: list[Position], is_free: Callable[[Position], bool]
) -> Position | None:
    candidates = [c for c in cells if is_free(c)]
    return rng.choice(candidates) if candidates else None
