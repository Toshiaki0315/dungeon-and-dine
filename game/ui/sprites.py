"""sprites.json を介したスプライト描画。仕様書 2.3.1。

素材の位置は sprites.json だけで決まるので、JSON を書き換えれば表示が切り替わる。
"""

from __future__ import annotations

import pyxel

from game import config
from game.data_loader import SpriteDef

COLOR_COUNT = 16  # Pyxel のパレットの色数
# 縁取りをずらす方向（上下左右の1px。斜めは入れず、絵が太らないようにする）
OUTLINE_OFFSETS: tuple[tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


class SpriteSheet:
    def __init__(self, defs: dict[str, SpriteDef]) -> None:
        self._defs = defs

    def has(self, name: str) -> bool:
        return name in self._defs

    def draw_scaled(
        self,
        name: str,
        x: int,
        y: int,
        scale: int,
        frame: int = 0,
        colkey: int | None = config.TRANSPARENT_COLOR,
    ) -> None:
        """8×8 の素材を拡大して描く（タイトル・拠点の絵。仕様書 14章）。"""
        sprite = self._defs[name]
        image = pyxel.images[sprite.bank]
        u = sprite.u + (frame % sprite.frames) * sprite.w
        for j in range(sprite.h):
            for i in range(sprite.w):
                color = image.pget(u + i, sprite.v + j)
                if colkey is not None and color == colkey:
                    continue
                pyxel.rect(x + i * scale, y + j * scale, scale, scale, color)

    def draw(
        self,
        name: str,
        x: int,
        y: int,
        frame: int = 0,
        colkey: int | None = config.TRANSPARENT_COLOR,
        offset: bool = False,
        outline: int | None = None,
    ) -> None:
        """スプライトを描く。frame はフレーム数で割った余りを使う（横に並んだ次のコマ）。

        offset を True にすると、8×8 より大きい素材（ボス）をマスの中央に寄せて描く。
        outline に色を渡すと、その色で1px の縁取りを付ける（仕様書 2.3.1）。
        16色しかないため、敵や落ちているものが床と同じ色になることを避けられない。
        縁取りで輪郭を分離して、どのエリアでも見分けられるようにする。
        """
        sprite = self._defs[name]
        u = sprite.u + (frame % sprite.frames) * sprite.w
        if offset:
            x -= (sprite.w - config.TILE_SIZE) // 2
            y -= (sprite.h - config.TILE_SIZE) // 2
        if outline is not None and colkey is not None:
            # 全色を縁の色に差し替えて、上下左右へ1pxずらした影を描く。
            # 透明の判定は差し替える前の色で行われるため、輪郭だけが残る。
            for color in range(1, COLOR_COUNT):
                pyxel.pal(color, outline)
            for dx, dy in OUTLINE_OFFSETS:
                pyxel.blt(x + dx, y + dy, sprite.bank, u, sprite.v, sprite.w, sprite.h, colkey)
            pyxel.pal()
        if colkey is None:
            pyxel.blt(x, y, sprite.bank, u, sprite.v, sprite.w, sprite.h)
        else:
            pyxel.blt(x, y, sprite.bank, u, sprite.v, sprite.w, sprite.h, colkey)
