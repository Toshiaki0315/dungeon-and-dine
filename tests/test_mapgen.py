from collections import deque
from dataclasses import replace

import pytest

from game import data_loader, rng
from game.world.direction import Direction
from game.world.floor import Floor
from game.world.mapgen import MapGenError, MapGenParams, generate_floor
from game.world.tiles import Tile

PARAMS = MapGenParams.from_dict(data_loader.load_all()["balance"]["mapgen"])
SEEDS = range(200)


def generate(seed: int, floor_number: int = 1, params: MapGenParams = PARAMS) -> Floor:
    return generate_floor(rng.floor_rng(seed, floor_number), floor_number, params)


def reachable_cells(floor: Floor) -> set[tuple[int, int]]:
    """開始位置から、移動ルール（8方向・角抜け禁止）で到達できるマス。"""
    seen = {floor.start}
    queue = deque([floor.start])
    while queue:
        x, y = queue.popleft()
        for direction in Direction:
            if floor.can_move(x, y, direction):
                nxt = (x + direction.dx, y + direction.dy)
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    return seen


def test_same_seed_generates_same_map():
    assert generate(42) == generate(42)


def test_different_seed_or_floor_generates_different_map():
    assert generate(42).tiles != generate(43).tiles
    assert generate(42, 1).tiles != generate(42, 2).tiles


def test_map_size_matches_params():
    floor = generate(0)
    assert (floor.width, floor.height) == (PARAMS.width, PARAMS.height)


@pytest.mark.parametrize("seed", SEEDS)
def test_all_rooms_and_stairs_are_reachable(seed):
    floor = generate(seed)
    reachable = reachable_cells(floor)
    for room in floor.rooms:
        assert set(room.cells()) <= reachable
    assert floor.stairs in reachable


def test_room_count_is_within_range():
    for seed in SEEDS:
        assert PARAMS.rooms_min <= len(generate(seed).rooms) <= PARAMS.rooms_max


def test_rooms_do_not_overlap_and_border_is_wall():
    for seed in SEEDS:
        floor = generate(seed)
        for i, a in enumerate(floor.rooms):
            for b in floor.rooms[i + 1 :]:
                assert not a.intersects(b)
        for x in range(floor.width):
            assert floor.tile_at(x, 0) == Tile.WALL
            assert floor.tile_at(x, floor.height - 1) == Tile.WALL
        for y in range(floor.height):
            assert floor.tile_at(0, y) == Tile.WALL
            assert floor.tile_at(floor.width - 1, y) == Tile.WALL


def test_one_stairs_in_a_different_room_from_start():
    for seed in SEEDS:
        floor = generate(seed)
        assert floor.tiles.count(Tile.STAIRS_DOWN) == 1
        assert floor.tile_at(*floor.stairs) == Tile.STAIRS_DOWN
        assert floor.room_at(*floor.start) != floor.room_at(*floor.stairs)
        assert floor.is_walkable(*floor.start)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        generate(0, params=replace(PARAMS, rooms_min=1))
    with pytest.raises(ValueError):
        generate(0, params=replace(PARAMS, leaf_min_w=PARAMS.room_min_w + 1))


def test_too_small_map_raises():
    with pytest.raises(MapGenError):
        generate(0, params=replace(PARAMS, width=16, height=12))


def test_from_dict_requires_all_keys():
    with pytest.raises(ValueError, match="rooms_max"):
        MapGenParams.from_dict({"width": 64, "height": 48, "rooms_min": 4})
