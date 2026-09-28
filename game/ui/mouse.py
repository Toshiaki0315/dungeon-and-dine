"""マウスの当たり判定（メニュー画面で共通に使う）。仕様書 14章。

画面ごとに、描画と同じ座標を使って「クリックした行・ボタン」を求める。
左クリックは決定、右クリックはキャンセルに対応させる。
"""

from __future__ import annotations

Pos = tuple[int, int]
Rect = tuple[int, int, int, int]  # x, y, w, h


def inside(pos: Pos, rect: Rect) -> bool:
    x, y, w, h = rect
    return x <= pos[0] < x + w and y <= pos[1] < y + h


def index_at(
    pos: Pos, x: int, y: int, w: int, step: int, count: int, height: int | None = None
) -> int | None:
    """縦に step ずつ並ぶ行のうち、クリックした行の番号。並びの外なら None。

    height を渡すと、行の隙間（step より低い行）をクリックしたときは None にする。
    """
    if count <= 0 or step <= 0 or not (x <= pos[0] < x + w) or pos[1] < y:
        return None
    index, offset = divmod(pos[1] - y, step)
    if index >= count or (height is not None and offset >= height):
        return None
    return index


def index_of(pos: Pos, rects: list[Rect]) -> int | None:
    """並べたボタンのうち、クリックしたものの番号。"""
    return next((i for i, rect in enumerate(rects) if inside(pos, rect)), None)
