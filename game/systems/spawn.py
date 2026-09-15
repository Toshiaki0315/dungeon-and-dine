"""敵・アイテム・宝箱・罠の配置。仕様書 5.3 / 11.3 / 12.2。

pyxel を import しないこと。
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from game.data_loader import dataclass_from_dict
from game.entities.item import GOLD_ID, Chest, FloorItem, ItemDef, ItemInstance
from game.entities.monster import Monster
from game.rng import weighted_choice
from game.systems.combat import round_half_up
from game.systems.equipment import EquipmentParams, generate_equipment
from game.systems.traps import Trap
from game.world.floor import Floor
from game.world.tiles import Tile

if TYPE_CHECKING:
    from game.systems.catalog import Catalog

Position = tuple[int, int]

CHEST_EQUIPMENT = "equipment"
CHEST_CONSUMABLE = "consumable"
CHEST_GOLD = "gold"


@dataclass(frozen=True)
class SpawnParams:
    """配置のパラメータ。balance.json の "spawn" で定義する。"""

    monsters_min: int
    monsters_max: int
    items_min: int
    items_max: int
    traps_min: int
    traps_max: int
    chests_min: int
    chests_max: int
    chest_trap_chance: int
    chest_contents: dict[str, int]  # 中身の種類 → 重み（equipment / consumable / gold）
    gold_min: int
    gold_max: int
    gold_per_floor_ratio: float  # 階層係数 = 1 + ratio × (階層 - 1)
    respawn_interval: int
    monster_gold_drop_chance: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SpawnParams:
        return dataclass_from_dict(cls, data, "spawn")


def gold_amount(rng: random.Random, floor_number: int, params: SpawnParams) -> int:
    factor = 1 + params.gold_per_floor_ratio * (floor_number - 1)
    return round_half_up(rng.randint(params.gold_min, params.gold_max) * factor)


def populate_floor(
    floor: Floor,
    rng: random.Random,
    catalog: Catalog,
    params: SpawnParams,
    equipment: EquipmentParams,
    next_uid: Callable[[], int],
) -> None:
    """生成したばかりの階に、敵・床アイテム・宝箱・罠を置く。"""
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

    def is_empty(cell: Position) -> bool:
        return (
            floor.item_at(*cell) is None
            and floor.trap_at(*cell) is None
            and floor.chest_at(*cell) is None
        )

    for _ in range(rng.randint(params.chests_min, params.chests_max)):
        cell = _pick_free(rng, room_cells, is_empty)
        if cell is None:
            break
        contents = chest_contents(rng, catalog, floor.number, params, equipment)
        trapped = rng.randrange(100) < params.chest_trap_chance
        floor.chests.append(Chest(contents, *cell, trapped=trapped))

    # 敵はプレイヤーのいる部屋には置かない
    monster_cells = [
        c
        for c in walkable
        if c != floor.start and (start_room is None or not start_room.contains(*c))
    ]
    for _ in range(rng.randint(params.monsters_min, params.monsters_max)):
        cell = _pick_free(
            rng,
            monster_cells,
            lambda c: floor.monster_at(*c) is None and floor.chest_at(*c) is None,
        )
        if cell is None:
            break
        spawn_monster(floor, rng, catalog, cell, next_uid)

    for _ in range(rng.randint(params.items_min, params.items_max)):
        cell = _pick_free(rng, room_cells, is_empty)
        if cell is None:
            break
        item = random_floor_item(rng, catalog, floor.number, params, equipment)
        floor.items.append(FloorItem(item, *cell))

    for _ in range(rng.randint(params.traps_min, params.traps_max)):
        cell = _pick_free(rng, room_cells, is_empty)
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
        if floor.is_walkable(x, y)
        and floor.monster_at(x, y) is None
        and floor.chest_at(x, y) is None
        and is_allowed((x, y))
    ]
    if not cells:
        return None
    return spawn_monster(floor, rng, catalog, rng.choice(cells), next_uid)


def make_item(
    definition: ItemDef,
    rng: random.Random,
    floor_number: int,
    params: SpawnParams,
    equipment: EquipmentParams,
) -> ItemInstance:
    """ダンジョンに置くアイテムの個体を作る（装備は未鑑定、お金は階層に応じた額）。"""
    if definition.is_equipment:
        return generate_equipment(definition, rng, floor_number, equipment)
    if definition.id == GOLD_ID:
        return ItemInstance(definition, gold_amount(rng, floor_number, params))
    if definition.stackable:
        return ItemInstance(definition, rng.randint(*definition.spawn_count))
    return ItemInstance(definition)


def random_floor_item(
    rng: random.Random,
    catalog: Catalog,
    floor_number: int,
    params: SpawnParams,
    equipment: EquipmentParams,
) -> ItemInstance:
    item_id = weighted_choice(rng, {i.id: i.spawn_weight for i in catalog.items.values()})
    assert item_id is not None, "spawn_weight が正のアイテムがありません"
    return make_item(catalog.items[item_id], rng, floor_number, params, equipment)


def chest_contents(
    rng: random.Random,
    catalog: Catalog,
    floor_number: int,
    params: SpawnParams,
    equipment: EquipmentParams,
) -> ItemInstance:
    """宝箱の中身（装備70%、消費アイテム20%、お金10%【仮】）。"""
    kind = weighted_choice(rng, params.chest_contents)
    if kind == CHEST_GOLD:
        return ItemInstance(catalog.items[GOLD_ID], gold_amount(rng, floor_number, params))
    if kind == CHEST_EQUIPMENT:
        pool = [i for i in catalog.items.values() if i.is_equipment]
    else:
        pool = [i for i in catalog.items.values() if not i.is_equipment and i.id != GOLD_ID]
    item_id = weighted_choice(rng, {i.id: i.spawn_weight for i in pool})
    assert item_id is not None, f"宝箱の中身（{kind}）に使えるアイテムがありません"
    return make_item(catalog.items[item_id], rng, floor_number, params, equipment)


def _pick_free(
    rng: random.Random, cells: list[Position], is_free: Callable[[Position], bool]
) -> Position | None:
    candidates = [c for c in cells if is_free(c)]
    return rng.choice(candidates) if candidates else None
