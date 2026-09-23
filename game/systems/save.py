"""meta.json / run.json の保存・読み込み。仕様書 13章。

pyxel を import しないこと（保存先パスは引数で受け取る）。
書き込みは一時ファイルに書いてからリネームし、途中で落ちてもファイルが壊れないようにする。
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from game.entities.item import SLOTS, Chest, EquipmentTrait, FloorItem, ItemInstance
from game.entities.monster import Monster
from game.entities.player import PLAYER_NAME, Player, normalize_appearance
from game.systems.catalog import Catalog
from game.systems.cooking import Notebook
from game.systems.inventory import Inventory
from game.systems.meta import BaseCampParams, Loadout, MetaProgress, ScoreEntry
from game.systems.traps import Trap
from game.world.direction import Direction
from game.world.floor import Campfire, Floor, Rect
from game.world.fov import FogMap
from game.world.tiles import Tile

if TYPE_CHECKING:
    from game.systems.game_state import GameParams, GameState

META_FILE = "meta.json"
RUN_FILE = "run.json"
META_VERSION = 1
RUN_VERSION = 1


# --- ファイル入出力 ---


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    """一時ファイルに書いてからリネームする（仕様書 13章）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(temp, path)


def read_json(path: Path) -> dict[str, Any] | None:
    """読み込む。ファイルがない、壊れている、形式が違うときは None を返す。"""
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def run_exists(save_dir: Path) -> bool:
    return (save_dir / RUN_FILE).exists()


def delete_run(save_dir: Path) -> None:
    """中断データを消す（読み込んだ直後、死亡・生還・クリアのとき）。"""
    (save_dir / RUN_FILE).unlink(missing_ok=True)


# --- アイテム ---


def traits_by_id(params: GameParams) -> dict[str, EquipmentTrait]:
    equipment = params.equipment
    return {t.id: t for t in (*equipment.marks, *equipment.curses)}


def item_to_dict(item: ItemInstance) -> dict[str, Any]:
    data: dict[str, Any] = {"id": item.id}
    if item.count != 1:
        data["count"] = item.count
    if item.modifier:
        data["modifier"] = item.modifier
    if item.mark is not None:
        data["mark"] = item.mark.id
    if item.curse is not None:
        data["curse"] = item.curse.id
    if not item.identified:
        data["identified"] = False
    if not item.curse_known:
        data["curse_known"] = False
    if item.rot_at is not None:
        data["rot_at"] = item.rot_at
    if item.charges != item.definition.charges:
        data["charges"] = item.charges
    return data


def item_from_dict(
    data: Mapping[str, Any], catalog: Catalog, traits: Mapping[str, EquipmentTrait]
) -> ItemInstance:
    mark, curse = data.get("mark"), data.get("curse")
    return ItemInstance(
        catalog.items[data["id"]],
        count=int(data.get("count", 1)),
        modifier=int(data.get("modifier", 0)),
        mark=traits[mark] if mark is not None else None,
        curse=traits[curse] if curse is not None else None,
        identified=bool(data.get("identified", True)),
        curse_known=bool(data.get("curse_known", True)),
        rot_at=data.get("rot_at"),
        charges=data.get("charges"),
    )


def inventory_to_dict(inventory: Inventory) -> dict[str, Any]:
    return {
        "capacity": inventory.capacity,
        "items": [item_to_dict(item) for item in inventory.items],
    }


def inventory_from_dict(
    data: Mapping[str, Any],
    catalog: Catalog,
    traits: Mapping[str, EquipmentTrait],
    params: GameParams,
) -> Inventory:
    inventory = Inventory(
        int(data["capacity"]), params.inventory_stack_max, params.inventory_item_stack_max
    )
    inventory.items = [item_from_dict(d, catalog, traits) for d in data["items"]]
    return inventory


def equipment_to_dict(
    equipment: Mapping[str, ItemInstance | None], items: list[ItemInstance]
) -> dict[str, int | None]:
    """装備は、持ち物の何番目かで持つ（同じ個体を指すため）。"""
    result: dict[str, int | None] = {}
    for slot in SLOTS:
        item = equipment.get(slot)
        result[slot] = next((i for i, other in enumerate(items) if other is item), None)
    return result


def equipment_from_dict(
    data: Mapping[str, Any], items: list[ItemInstance]
) -> dict[str, ItemInstance | None]:
    equipment: dict[str, ItemInstance | None] = dict.fromkeys(SLOTS)
    for slot in SLOTS:
        index = data.get(slot)
        if index is not None and 0 <= int(index) < len(items):
            equipment[slot] = items[int(index)]
    return equipment


# --- meta.json ---


def meta_to_dict(meta: MetaProgress) -> dict[str, Any]:
    return {
        "version": META_VERSION,
        "funds": meta.funds,
        "loadout": {
            "items": inventory_to_dict(meta.loadout.items),
            "equipment": equipment_to_dict(meta.loadout.equipment, meta.loadout.items.items),
        },
        "storage": inventory_to_dict(meta.storage),
        "notebook": {
            "discovered": list(meta.notebook.discovered),
            "failures": [list(key) for key in meta.notebook.failures],
        },
        "inventory_expansions": meta.inventory_expansions,
        "storage_expansions": meta.storage_expansions,
        "clears": meta.clears,
        "deepest_floor": meta.deepest_floor,
        "player_name": meta.player_name,
        "appearance": meta.appearance,
        "scores": [
            {
                "name": s.name,
                "floor": s.floor,
                "gold": s.gold,
                "turn": s.turn,
                "outcome": s.outcome,
            }
            for s in meta.scores
        ],
    }


def meta_from_dict(
    data: Mapping[str, Any], params: GameParams, camp: BaseCampParams
) -> MetaProgress:
    catalog, traits = params.catalog, traits_by_id(params)
    items = inventory_from_dict(data["loadout"]["items"], catalog, traits, params)
    notebook = Notebook(
        discovered=list(data["notebook"]["discovered"]),
        failures=[tuple(key) for key in data["notebook"]["failures"]],
    )
    return MetaProgress(
        loadout=Loadout(items, equipment_from_dict(data["loadout"]["equipment"], items.items)),
        storage=inventory_from_dict(data["storage"], catalog, traits, params),
        notebook=notebook,
        funds=int(data["funds"]),
        inventory_expansions=int(data["inventory_expansions"]),
        storage_expansions=int(data["storage_expansions"]),
        clears=int(data["clears"]),
        deepest_floor=int(data["deepest_floor"]),
        # 名前・見た目・ランキングは後から加えた項目なので、古いセーブデータでも読めるようにする
        player_name=str(data.get("player_name") or PLAYER_NAME),
        appearance=normalize_appearance(data.get("appearance")),
        scores=[
            ScoreEntry(
                str(s["name"]),
                int(s["floor"]),
                int(s["gold"]),
                int(s["turn"]),
                str(s["outcome"]),
            )
            for s in data.get("scores", ())
        ],
    )


def save_meta(save_dir: Path, meta: MetaProgress) -> None:
    write_json(save_dir / META_FILE, meta_to_dict(meta))


def load_meta(save_dir: Path, params: GameParams, camp: BaseCampParams) -> MetaProgress:
    """meta.json を読み込む。ないときや壊れているときは、新しいデータを返す。"""
    data = read_json(save_dir / META_FILE)
    if data is None or data.get("version") != META_VERSION:
        return new_meta(params, camp)
    try:
        return meta_from_dict(data, params, camp)
    except (KeyError, TypeError, ValueError):
        return new_meta(params, camp)


def new_meta(params: GameParams, camp: BaseCampParams) -> MetaProgress:
    return MetaProgress.new(
        params.inventory_capacity,
        params.inventory_stack_max,
        params.inventory_item_stack_max,
        camp,
    )


# --- run.json ---


def player_to_dict(player: Player, items: list[ItemInstance]) -> dict[str, Any]:
    return {
        "name": player.name,
        "appearance": player.appearance,
        "x": player.x,
        "y": player.y,
        "facing": player.facing.name,
        "speed": player.speed,
        "energy": player.energy,
        "statuses": player.statuses.snapshot(),
        "level": player.level,
        "exp": player.exp,
        "gold": player.gold,
        "hp": player.hp,
        "max_hp": player.max_hp,
        "mp": player.mp,
        "max_mp": player.max_mp,
        "atk": player.atk,
        "defense": player.defense,
        "hit": player.hit,
        "evade": player.evade,
        "satiety": player.satiety,
        "max_satiety": player.max_satiety,
        "satiety_progress": player.satiety_progress,
        "skills": list(player.skills),
        "equipment": equipment_to_dict(player.equipment, items),
    }


def player_from_dict(data: Mapping[str, Any], items: list[ItemInstance]) -> Player:
    player = Player(
        name=str(data.get("name") or PLAYER_NAME),
        # 見た目は後から加えた項目なので、古いセーブデータでも読めるようにする
        appearance=normalize_appearance(data.get("appearance")),
        x=int(data["x"]),
        y=int(data["y"]),
        facing=Direction[data["facing"]],
        speed=int(data["speed"]),
        energy=int(data["energy"]),
        level=int(data["level"]),
        exp=int(data["exp"]),
        gold=int(data["gold"]),
        hp=int(data["hp"]),
        max_hp=int(data["max_hp"]),
        mp=int(data["mp"]),
        max_mp=int(data["max_mp"]),
        atk=int(data["atk"]),
        defense=int(data["defense"]),
        hit=int(data["hit"]),
        evade=int(data["evade"]),
        satiety=int(data["satiety"]),
        max_satiety=int(data["max_satiety"]),
        satiety_progress=int(data["satiety_progress"]),
        skills=list(data["skills"]),
    )
    player.statuses.restore(data["statuses"])
    player.equipment = equipment_from_dict(data["equipment"], items)
    return player


def monster_to_dict(monster: Monster) -> dict[str, Any]:
    return {
        "id": monster.definition.id,
        "uid": monster.uid,
        "x": monster.x,
        "y": monster.y,
        "facing": monster.facing.name,
        "speed": monster.speed,
        "energy": monster.energy,
        "hp": monster.hp,
        "mode": monster.mode,
        "target": list(monster.target) if monster.target is not None else None,
        "disguised": monster.disguised,
        "turns_acted": monster.turns_acted,
        "statuses": monster.statuses.snapshot(),
    }


def monster_from_dict(data: Mapping[str, Any], catalog: Catalog) -> Monster:
    target = data.get("target")
    monster = Monster(
        x=int(data["x"]),
        y=int(data["y"]),
        facing=Direction[data["facing"]],
        speed=int(data["speed"]),
        energy=int(data["energy"]),
        definition=catalog.monsters[data["id"]],
        uid=int(data["uid"]),
        hp=int(data["hp"]),
        mode=str(data["mode"]),
        target=(int(target[0]), int(target[1])) if target is not None else None,
        disguised=bool(data["disguised"]),
        turns_acted=int(data.get("turns_acted", 0)),
    )
    monster.statuses.restore(data["statuses"])
    return monster


def floor_to_dict(floor: Floor) -> dict[str, Any]:
    return {
        "number": floor.number,
        "width": floor.width,
        "height": floor.height,
        "tiles": "".join(str(int(tile)) for tile in floor.tiles),
        "rooms": [[r.x, r.y, r.w, r.h] for r in floor.rooms],
        "start": list(floor.start),
        "stairs": list(floor.stairs),
        "monsters": [monster_to_dict(m) for m in floor.monsters],
        "items": [{"item": item_to_dict(f.item), "x": f.x, "y": f.y} for f in floor.items],
        "chests": [
            {
                "contents": item_to_dict(c.contents),
                "x": c.x,
                "y": c.y,
                "trapped": c.trapped,
                "opened": c.opened,
            }
            for c in floor.chests
        ],
        "traps": [
            {"id": t.definition.id, "x": t.x, "y": t.y, "discovered": t.discovered}
            for t in floor.traps
        ],
        "campfires": [{"x": c.x, "y": c.y, "expires_at": c.expires_at} for c in floor.campfires],
        "kindled": floor.kindled,
    }


def floor_from_dict(
    data: Mapping[str, Any], catalog: Catalog, traits: Mapping[str, EquipmentTrait]
) -> Floor:
    floor = Floor(
        number=int(data["number"]),
        width=int(data["width"]),
        height=int(data["height"]),
        tiles=[Tile(int(c)) for c in data["tiles"]],
        rooms=[Rect(*room) for room in data["rooms"]],
        start=(int(data["start"][0]), int(data["start"][1])),
        stairs=(int(data["stairs"][0]), int(data["stairs"][1])),
    )
    floor.monsters = [monster_from_dict(m, catalog) for m in data["monsters"]]
    floor.items = [
        FloorItem(item_from_dict(f["item"], catalog, traits), int(f["x"]), int(f["y"]))
        for f in data["items"]
    ]
    floor.chests = [
        Chest(
            item_from_dict(c["contents"], catalog, traits),
            int(c["x"]),
            int(c["y"]),
            trapped=bool(c["trapped"]),
            opened=bool(c["opened"]),
        )
        for c in data["chests"]
    ]
    floor.traps = [
        Trap(catalog.traps[t["id"]], int(t["x"]), int(t["y"]), bool(t["discovered"]))
        for t in data["traps"]
    ]
    floor.campfires = [
        Campfire(int(c["x"]), int(c["y"]), c["expires_at"]) for c in data["campfires"]
    ]
    floor.kindled = bool(data["kindled"])
    return floor


def state_to_dict(state: GameState) -> dict[str, Any]:
    items = state.inventory.items
    rng_version, rng_internal, rng_gauss = state.rng.getstate()
    return {
        "version": RUN_VERSION,
        "run_seed": state.run_seed,
        "turn": state.turn,
        "uid_counter": state.uid_counter,
        "rng": [rng_version, list(rng_internal), rng_gauss],
        "player": player_to_dict(state.player, items),
        "inventory": inventory_to_dict(state.inventory),
        "bag_bonus": state.bag_bonus,
        "floor": floor_to_dict(state.floor),
        "fog": state.fog.explored_bits(),
        "log": state.log.entries,
    }


def state_from_dict(data: Mapping[str, Any], params: GameParams, notebook: Notebook) -> GameState:
    from game.systems.game_state import GameState  # 循環 import を避けるため、ここで読み込む

    catalog, traits = params.catalog, traits_by_id(params)
    state = GameState(int(data["run_seed"]), params, notebook, generate=False)
    state.inventory = inventory_from_dict(data["inventory"], catalog, traits, params)
    state.player = player_from_dict(data["player"], state.inventory.items)
    state.floor = floor_from_dict(data["floor"], catalog, traits)
    state.area = area_of(params, state.floor.number)
    state.fog = FogMap(state.floor.width, state.floor.height)
    state.fog.restore_bits(data["fog"])
    state.scheduler.turn = int(data["turn"])
    state.uid_counter = int(data["uid_counter"])
    state.bag_bonus = int(data.get("bag_bonus", 0))  # 背負い袋を足す前のセーブデータには無い
    rng_version, rng_internal, rng_gauss = data["rng"]
    state.rng.setstate((int(rng_version), tuple(int(v) for v in rng_internal), rng_gauss))
    for entry in data["log"]:
        state.log.add(entry)
    state.update_fov()
    return state


def area_of(params: GameParams, floor_number: int):  # noqa: ANN201
    from game.world.floor import area_for_floor

    return area_for_floor(params.areas, floor_number)


def save_run(save_dir: Path, state: GameState) -> None:
    write_json(save_dir / RUN_FILE, state_to_dict(state))


def load_run(save_dir: Path, params: GameParams, notebook: Notebook) -> GameState | None:
    """run.json を読み込む。ないときや壊れているときは None を返す。"""
    data = read_json(save_dir / RUN_FILE)
    if data is None or data.get("version") != RUN_VERSION:
        return None
    try:
        return state_from_dict(data, params, notebook)
    except (KeyError, TypeError, ValueError):
        return None
