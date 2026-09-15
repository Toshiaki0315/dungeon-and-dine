"""カメラ位置の計算。仕様書 2.3。

計算だけを行うので pyxel には依存しない。
"""

from __future__ import annotations


def camera_origin(
    target_x: int, target_y: int, map_w: int, map_h: int, view_w: int, view_h: int
) -> tuple[int, int]:
    """表示領域の左上に来るタイル座標を返す。

    対象を画面中央に置き、マップの端ではマップ外が映らないように止める。
    マップが表示領域より小さい軸は中央に寄せる。
    """
    return (_axis(target_x, map_w, view_w), _axis(target_y, map_h, view_h))


def _axis(target: int, map_size: int, view_size: int) -> int:
    if map_size <= view_size:
        return -((view_size - map_size) // 2)
    return max(0, min(target - view_size // 2, map_size - view_size))
