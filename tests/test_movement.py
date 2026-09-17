import pytest

from game.entities.player import (
    APPEARANCE_IDS,
    APPEARANCES,
    DEFAULT_APPEARANCE,
    PLAYER_SPRITE_NAMES,
    Player,
    normalize_appearance,
)
from game.world.direction import FACINGS, Direction
from game.world.floor import Floor
from game.world.tiles import Tile

# テスト用のマップ定義（ゲーム画面の表示ではない）
LEGEND = {"#": Tile.WALL, ".": Tile.FLOOR, "=": Tile.CORRIDOR, ">": Tile.STAIRS_DOWN}


def make_floor(rows: list[str]) -> Floor:
    tiles = [LEGEND[c] for row in rows for c in row]
    return Floor(
        number=1,
        width=len(rows[0]),
        height=len(rows),
        tiles=tiles,
        rooms=[],
        start=(1, 1),
        stairs=(0, 0),
    )


OPEN = make_floor(
    [
        "#####",
        "#...#",
        "#...#",
        "#..>#",
        "#####",
    ]
)

PILLAR = make_floor(
    [
        "#####",
        "#...#",
        "#.#.#",
        "#...#",
        "#####",
    ]
)


@pytest.mark.parametrize("direction", list(Direction))
def test_can_move_in_all_eight_directions_in_open_space(direction):
    player = Player(2, 2)
    assert player.try_move(OPEN, direction)
    assert player.pos == (2 + direction.dx, 2 + direction.dy)
    assert player.facing == direction


def test_wall_blocks_movement_but_changes_facing():
    player = Player(1, 1)
    assert not player.try_move(OPEN, Direction.UP)
    assert player.pos == (1, 1)
    assert player.facing == Direction.UP


@pytest.mark.parametrize(
    ("start", "direction"),
    [
        ((1, 1), Direction.DOWN_RIGHT),  # 右下が柱
        ((3, 1), Direction.DOWN_LEFT),
        ((1, 3), Direction.UP_RIGHT),
        ((3, 3), Direction.UP_LEFT),
    ],
)
def test_diagonal_into_wall_is_blocked(start, direction):
    player = Player(*start)
    assert not player.try_move(PILLAR, direction)
    assert player.pos == start


@pytest.mark.parametrize(
    ("start", "direction"),
    [
        ((2, 1), Direction.DOWN_LEFT),  # 左は床、下は柱 → 角抜け
        ((2, 1), Direction.DOWN_RIGHT),
        ((1, 2), Direction.UP_RIGHT),  # 上は床、右は柱
        ((3, 2), Direction.DOWN_LEFT),
    ],
)
def test_corner_cutting_is_blocked(start, direction):
    player = Player(*start)
    assert not player.try_move(PILLAR, direction)
    assert player.pos == start


def test_stairs_and_corridor_are_walkable():
    floor = make_floor(["#=>#"])
    player = Player(1, 0)
    assert player.try_move(floor, Direction.RIGHT)
    assert player.pos == (2, 0)


def test_outside_of_map_is_treated_as_wall():
    floor = make_floor(["..", ".."])
    player = Player(0, 0)
    assert not player.try_move(floor, Direction.LEFT)
    assert not player.try_move(floor, Direction.UP_LEFT)
    assert floor.tile_at(-1, 0) == Tile.WALL


def test_edge_wall_is_only_wall_touching_walkable_tiles():
    floor = make_floor(
        [
            "#####",
            "#####",
            "##.##",
            "#####",
            "#####",
        ]
    )
    assert floor.is_edge_wall(1, 1)  # 斜めに接する
    assert floor.is_edge_wall(2, 3)
    assert not floor.is_edge_wall(0, 0)  # 岩盤
    assert not floor.is_edge_wall(2, 2)  # 床は壁ではない


def test_player_sprite_uses_left_right_for_diagonals():
    player = Player(2, 2)
    expected = {
        Direction.UP: "hero_warrior_up",
        Direction.DOWN: "hero_warrior_down",
        Direction.UP_LEFT: "hero_warrior_left",
        Direction.DOWN_LEFT: "hero_warrior_left",
        Direction.UP_RIGHT: "hero_warrior_right",
        Direction.DOWN_RIGHT: "hero_warrior_right",
    }
    for direction, name in expected.items():
        player.facing = direction
        assert player.sprite_name == name


def test_player_sprite_follows_the_chosen_appearance():
    player = Player(2, 2, appearance="mage")
    player.facing = Direction.DOWN_LEFT
    assert player.sprite_name == "hero_mage_left"


def test_unknown_appearance_falls_back_to_the_default():
    assert normalize_appearance("priest") == "priest"
    assert normalize_appearance("ninja") == DEFAULT_APPEARANCE
    assert normalize_appearance(None) == DEFAULT_APPEARANCE


def test_every_appearance_has_sprites_for_every_facing():
    assert len(PLAYER_SPRITE_NAMES) == len(APPEARANCE_IDS) * len(FACINGS)
    assert len(set(APPEARANCE_IDS)) == len(APPEARANCES) == 5
