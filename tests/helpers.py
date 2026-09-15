"""テスト用の共通ヘルパー。"""

import random

from game.world.floor import Floor, Rect
from game.world.tiles import Tile

LEGEND = {"#": Tile.WALL, ".": Tile.FLOOR, "=": Tile.CORRIDOR, ">": Tile.STAIRS_DOWN}


def make_floor(rows: list[str], rooms: list[Rect] | None = None) -> Floor:
    """文字列でテスト用のマップを作る（ゲーム画面の表示ではない）。"""
    return Floor(
        number=1,
        width=len(rows[0]),
        height=len(rows),
        tiles=[LEGEND[c] for row in rows for c in row],
        rooms=rooms or [],
        start=(1, 1),
        stairs=(0, 0),
    )


class FixedRng(random.Random):
    """randrange が常に roll（範囲内に丸める）を返し、uniform が中央値を返す乱数。

    choice / shuffle などは通常の乱数（シード0）のまま。
    """

    def __init__(self, roll: int = 50) -> None:
        super().__init__(0)
        self.roll = roll

    def randrange(self, start, stop=None, step=1):  # noqa: ANN001, ANN201
        if stop is None:
            start, stop = 0, start
        return max(start, min(start + self.roll, stop - 1))

    def uniform(self, a, b):  # noqa: ANN001, ANN201
        return (a + b) / 2
