from game.world.direction import Direction
from game.world.floor import Floor, Rect
from game.world.fov import FogMap, FovParams, Visibility, compute_visible
from game.world.tiles import Tile

PARAMS = FovParams(corridor_adjacent=1, corridor_forward=4)
LEGEND = {"#": Tile.WALL, ".": Tile.FLOOR, "=": Tile.CORRIDOR}

# テスト用のマップ定義（ゲーム画面の表示ではない）。部屋は (1,1)-(3,3)、通路は x=4..8
ROWS = [
    "##########",
    "#...######",
    "#...=====#",
    "#...######",
    "##########",
]
ROOM = Rect(1, 1, 3, 3)


def make_floor():
    return Floor(
        number=1,
        width=len(ROWS[0]),
        height=len(ROWS),
        tiles=[LEGEND[c] for row in ROWS for c in row],
        rooms=[ROOM],
        start=(2, 2),
        stairs=(0, 0),
    )


def test_whole_room_including_walls_is_visible_inside_room():
    floor = make_floor()
    visible = compute_visible(floor, 2, 2, Direction.DOWN, PARAMS)
    assert set(Rect(0, 0, 5, 5).cells()) <= visible
    assert (5, 2) not in visible


def test_corridor_shows_adjacent_and_forward_line_until_wall():
    floor = make_floor()
    visible = compute_visible(floor, 5, 2, Direction.RIGHT, PARAMS)
    adjacent = {(x, y) for x in range(4, 7) for y in range(1, 4)}
    assert adjacent <= visible
    assert {(7, 2), (8, 2), (9, 2)} <= visible  # 壁 (9,2) までは見える
    assert (2, 2) not in visible  # 部屋の中は見えない


def test_corridor_forward_range_is_limited():
    floor = make_floor()
    visible = compute_visible(floor, 8, 2, Direction.LEFT, PARAMS)
    assert {(7, 2), (6, 2), (5, 2), (4, 2)} <= visible
    assert (3, 2) not in visible


def test_adjacent_range_can_be_extended():
    floor = make_floor()
    wide = FovParams(corridor_adjacent=2, corridor_forward=4)
    visible = compute_visible(floor, 6, 2, Direction.UP, wide)
    assert (4, 0) in visible
    assert (4, 0) not in compute_visible(floor, 6, 2, Direction.UP, PARAMS)


def test_blind_sees_only_adjacent_even_in_room():
    floor = make_floor()
    visible = compute_visible(floor, 2, 2, Direction.DOWN, PARAMS, blind=True)
    assert visible == {(x, y) for x in range(1, 4) for y in range(1, 4)}


def test_fog_map_tracks_three_states():
    floor = make_floor()
    fog = FogMap(floor.width, floor.height)
    assert fog.state(2, 2) == Visibility.UNEXPLORED

    fog.update(compute_visible(floor, 2, 2, Direction.DOWN, PARAMS))
    assert fog.state(2, 2) == Visibility.VISIBLE

    fog.update(compute_visible(floor, 7, 2, Direction.RIGHT, PARAMS))
    assert fog.state(2, 2) == Visibility.KNOWN
    assert fog.state(7, 2) == Visibility.VISIBLE
    assert fog.state(0, 4) == Visibility.KNOWN
    assert fog.state(-1, 0) == Visibility.UNEXPLORED
