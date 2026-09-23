"""セーブ／ロード（meta.json / run.json）のテスト（フェーズ6）。仕様書 13章。"""

import json

from game.entities.item import SLOT_WEAPON, ItemInstance
from game.entities.player import DEFAULT_APPEARANCE
from game.systems import save
from game.systems.cooking import Notebook
from game.world.direction import Direction
from game.world.floor import Campfire
from tests.test_game_state import (
    CATALOG,
    PARAMS,
    new_state,
    place_item,
    place_monster,
    place_trap,
)

CAMP = PARAMS.base_camp


def played_state():
    """少し遊んだ状態（敵・罠・床アイテム・焚き火・持ち物・ログがある）を作る。"""
    state = new_state()
    place_monster(state, "giant_rat", Direction.RIGHT, distance=3)
    place_trap(state, "pit", Direction.LEFT)
    place_item(state, "herb", Direction.UP)
    state.floor.campfires.append(Campfire(state.player.x + 2, state.player.y, expires_at=30))
    knife = ItemInstance(CATALOG.items["knife"], modifier=1)
    state.inventory.add(knife)
    state.inventory.add(ItemInstance(CATALOG.items["spear"], identified=False, curse_known=False))
    state.equip(knife)
    state.player.hp -= 5
    state.notebook.discover("rat_skewer")
    state.move_player(Direction.DOWN)
    return state


def round_trip(tmp_path, state):
    save.save_run(tmp_path, state)
    restored = save.load_run(tmp_path, PARAMS, state.notebook)
    assert restored is not None
    return restored


# --- run.json ---


def test_run_round_trip_restores_the_player_and_inventory(tmp_path):
    state = played_state()
    restored = round_trip(tmp_path, state)

    assert restored.run_seed == state.run_seed
    assert restored.turn == state.turn
    assert restored.player.pos == state.player.pos
    assert restored.player.facing == state.player.facing
    assert restored.player.hp == state.player.hp
    assert restored.player.satiety == state.player.satiety
    assert restored.player.skills == state.player.skills
    assert [i.name for i in restored.inventory.items] == [i.name for i in state.inventory.items]
    assert restored.inventory.capacity == state.inventory.capacity


def test_run_round_trip_keeps_stacks_and_the_bag_bonus(tmp_path):
    state = played_state()
    state.inventory.add(ItemInstance(CATALOG.items["herb"], count=3))
    state.inventory.capacity += 5
    state.bag_bonus = 5
    restored = round_trip(tmp_path, state)
    assert [(i.id, i.count) for i in restored.inventory.items] == [
        (i.id, i.count) for i in state.inventory.items
    ]
    assert (restored.bag_bonus, restored.inventory.capacity) == (5, state.inventory.capacity)


def test_run_round_trip_keeps_the_appearance(tmp_path):
    state = played_state()
    state.player.appearance = "fighter"
    assert round_trip(tmp_path, state).player.appearance == "fighter"


def test_run_round_trip_keeps_equipment_pointing_at_the_carried_item(tmp_path):
    restored = round_trip(tmp_path, played_state())
    weapon = restored.player.equipment[SLOT_WEAPON]
    assert weapon is not None
    assert weapon in restored.inventory.items  # 持ち物の中の同じ個体を装備している
    assert weapon.modifier == 1


def test_run_round_trip_hides_unidentified_equipment(tmp_path):
    restored = round_trip(tmp_path, played_state())
    spear = next(i for i in restored.inventory.items if i.id == "spear")
    assert not spear.identified and not spear.curse_known
    assert spear.name == "？の槍"


def test_run_round_trip_restores_the_floor(tmp_path):
    state = played_state()
    restored = round_trip(tmp_path, state)

    assert restored.floor.number == state.floor.number
    assert restored.floor.tiles == state.floor.tiles
    assert restored.floor.start == state.floor.start and restored.floor.stairs == state.floor.stairs
    assert [r.center for r in restored.floor.rooms] == [r.center for r in state.floor.rooms]
    assert [(m.definition.id, m.uid, m.pos, m.hp) for m in restored.floor.monsters] == [
        (m.definition.id, m.uid, m.pos, m.hp) for m in state.floor.monsters
    ]
    assert [(t.definition.id, t.pos, t.discovered) for t in restored.floor.traps] == [
        (t.definition.id, t.pos, t.discovered) for t in state.floor.traps
    ]
    assert [(f.item.id, f.pos) for f in restored.floor.items] == [
        (f.item.id, f.pos) for f in state.floor.items
    ]
    assert [(c.pos, c.expires_at) for c in restored.floor.campfires] == [
        (c.pos, c.expires_at) for c in state.floor.campfires
    ]
    assert [(c.pos, c.trapped, c.opened) for c in restored.floor.chests] == [
        (c.pos, c.trapped, c.opened) for c in state.floor.chests
    ]


def test_run_round_trip_restores_fog_log_and_random(tmp_path):
    state = played_state()
    restored = round_trip(tmp_path, state)

    assert restored.fog.explored_bits() == state.fog.explored_bits()
    assert restored.log.entries == state.log.entries
    assert restored.uid_counter == state.uid_counter
    # 乱数の続きも同じ（再開しても出目が変わらない）
    assert [restored.rng.random() for _ in range(3)] == [state.rng.random() for _ in range(3)]


def test_run_round_trip_keeps_playing(tmp_path):
    """復元した状態から、そのまま続きを遊べる。"""
    restored = round_trip(tmp_path, played_state())
    before = restored.turn
    restored.wait()
    assert restored.turn == before + 1


def test_missing_or_broken_run_file_is_ignored(tmp_path):
    assert save.run_exists(tmp_path) is False
    assert save.load_run(tmp_path, PARAMS, Notebook()) is None

    (tmp_path / save.RUN_FILE).write_text("{壊れている", encoding="utf-8")
    assert save.load_run(tmp_path, PARAMS, Notebook()) is None

    (tmp_path / save.RUN_FILE).write_text('{"version": 999}', encoding="utf-8")
    assert save.load_run(tmp_path, PARAMS, Notebook()) is None


def test_deleting_the_run_file(tmp_path):
    save.save_run(tmp_path, played_state())
    assert save.run_exists(tmp_path)
    save.delete_run(tmp_path)
    assert not save.run_exists(tmp_path)
    save.delete_run(tmp_path)  # 2回目でも例外にならない


def test_writing_leaves_no_temporary_file(tmp_path):
    save.save_run(tmp_path, played_state())
    assert [p.name for p in tmp_path.iterdir()] == [save.RUN_FILE]
    assert json.loads((tmp_path / save.RUN_FILE).read_text(encoding="utf-8"))["version"] == 1


# --- meta.json ---


def filled_meta():
    meta = save.new_meta(PARAMS, CAMP)
    meta.funds = 1234
    knife = ItemInstance(CATALOG.items["knife"], modifier=2)
    meta.loadout.items.add(knife)
    meta.loadout.equipment[SLOT_WEAPON] = knife
    meta.storage.add(ItemInstance(CATALOG.items["herb"]))
    meta.notebook.discover("rat_skewer")
    meta.notebook.record_failure(("herb", "herb"))
    meta.inventory_expansions = 1
    meta.storage_expansions = 2
    meta.clears = 3
    meta.deepest_floor = 12
    return meta


def test_meta_round_trip(tmp_path):
    meta = filled_meta()
    save.save_meta(tmp_path, meta)
    restored = save.load_meta(tmp_path, PARAMS, CAMP)

    assert restored.funds == 1234
    assert [i.name for i in restored.loadout.items.items] == ["ナイフ+2"]
    assert restored.loadout.equipment[SLOT_WEAPON] is restored.loadout.items.items[0]
    assert [i.id for i in restored.storage.items] == ["herb"]
    assert restored.notebook.discovered == ["rat_skewer"]
    assert restored.notebook.failures == [("herb", "herb")]
    assert (restored.inventory_expansions, restored.storage_expansions) == (1, 2)
    assert (restored.clears, restored.deepest_floor) == (3, 12)


def test_meta_keeps_the_chosen_appearance(tmp_path):
    meta = filled_meta()
    meta.appearance = "priest"
    save.save_meta(tmp_path, meta)
    assert save.load_meta(tmp_path, PARAMS, CAMP).appearance == "priest"


def test_meta_without_appearance_uses_the_default(tmp_path):
    save.save_meta(tmp_path, filled_meta())
    path = tmp_path / save.META_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["appearance"]  # 見た目を選べるようになる前のセーブデータ
    path.write_text(json.dumps(data), encoding="utf-8")
    assert save.load_meta(tmp_path, PARAMS, CAMP).appearance == DEFAULT_APPEARANCE


def test_meta_keeps_expanded_capacities(tmp_path):
    meta = filled_meta()
    meta.loadout.items.capacity += 5
    meta.storage.capacity += 20
    save.save_meta(tmp_path, meta)
    restored = save.load_meta(tmp_path, PARAMS, CAMP)
    assert restored.loadout.items.capacity == PARAMS.inventory_capacity + 5
    assert restored.storage.capacity == CAMP.storage_capacity + 20


def test_missing_meta_file_starts_fresh(tmp_path):
    meta = save.load_meta(tmp_path, PARAMS, CAMP)
    assert meta.funds == 0 and meta.deepest_floor == 1
    assert meta.loadout.items.capacity == PARAMS.inventory_capacity
    assert meta.storage.capacity == CAMP.storage_capacity
    assert not meta.notebook.discovered


def test_broken_meta_file_starts_fresh(tmp_path):
    (tmp_path / save.META_FILE).write_text('{"version": 1}', encoding="utf-8")
    assert save.load_meta(tmp_path, PARAMS, CAMP).funds == 0


def test_run_and_meta_are_separate_files(tmp_path):
    save.save_meta(tmp_path, filled_meta())
    save.save_run(tmp_path, played_state())
    save.delete_run(tmp_path)
    assert save.load_meta(tmp_path, PARAMS, CAMP).funds == 1234  # 中断データを消しても残る
