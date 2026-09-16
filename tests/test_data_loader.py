import json

import pytest

from game import data_loader
from game.entities.player import PLAYER_SPRITE_NAMES
from game.world.floor import Area, area_for_floor
from game.world.tiles import SPRITE_NAMES


def test_all_data_files_load():
    data = data_loader.load_all()
    assert set(data) == {name.removesuffix(".json") for name in data_loader.REQUIRED_KEYS}


def test_missing_required_key_raises(tmp_path):
    for filename, required in data_loader.REQUIRED_KEYS.items():
        (tmp_path / filename).write_text(
            json.dumps({key: [] for key in required}), encoding="utf-8"
        )
    (tmp_path / "enemies.json").write_text(json.dumps({"version": 1}), encoding="utf-8")

    with pytest.raises(data_loader.DataValidationError, match="enemies"):
        data_loader.load_all(tmp_path)


def test_sprites_json_defines_all_required_sprites():
    from game.systems.catalog import Catalog

    data = data_loader.load_all()
    defs = data_loader.parse_sprites(data["sprites"])
    catalog = Catalog.from_data(data)
    data_loader.require_sprites(
        defs, [*SPRITE_NAMES.values(), *PLAYER_SPRITE_NAMES, *catalog.sprite_names()]
    )


def test_parse_sprites_applies_defaults_and_values():
    defs = data_loader.parse_sprites(
        {"image_bank": 0, "sprites": {"rat": {"u": 0, "v": 16, "frames": 2}}}
    )
    assert defs["rat"] == data_loader.SpriteDef(u=0, v=16, w=8, h=8, frames=2, bank=0)


def test_parse_sprites_rejects_invalid_entries():
    with pytest.raises(data_loader.DataValidationError, match="rat"):
        data_loader.parse_sprites({"sprites": {"rat": {"u": 0}}})
    with pytest.raises(data_loader.DataValidationError, match="frames"):
        data_loader.parse_sprites({"sprites": {"rat": {"u": 0, "v": 0, "frames": 0}}})


def test_require_sprites_reports_missing_names():
    defs = data_loader.parse_sprites({"sprites": {"floor": {"u": 0, "v": 0}}})
    with pytest.raises(data_loader.DataValidationError, match="wall"):
        data_loader.require_sprites(defs, ["floor", "wall"])


def test_every_floor_has_an_area():
    areas = [Area.from_dict(a) for a in data_loader.load_all()["floors"]["areas"]]
    assert area_for_floor(areas, 1).name == "苔むす洞窟"
    assert area_for_floor(areas, 20).name == "奈落の底"
    for floor_number in range(1, 21):
        area_for_floor(areas, floor_number)
    # 21階から下は、1周分のエリアをくり返して使う（B21F は B1F と同じエリア）
    assert area_for_floor(areas, 21).name == "苔むす洞窟"
    assert area_for_floor(areas, 40).name == "奈落の底"
    assert area_for_floor(areas, 101).name == "苔むす洞窟"
    with pytest.raises(ValueError):
        area_for_floor(areas, 0)  # 0階は存在しない
