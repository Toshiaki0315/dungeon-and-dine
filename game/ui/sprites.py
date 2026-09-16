"""sprites.json を介したスプライト描画。仕様書 2.3.1。

素材の位置は sprites.json だけで決まるので、JSON を書き換えれば表示が切り替わる。
"""

from __future__ import annotations

import pyxel

from game import config
from game.data_loader import SpriteDef


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
    ) -> None:
        """スプライトを描く。frame はフレーム数で割った余りを使う（横に並んだ次のコマ）。

        offset を True にすると、8×8 より大きい素材（ボス）をマスの中央に寄せて描く。
        """
        sprite = self._defs[name]
        u = sprite.u + (frame % sprite.frames) * sprite.w
        if offset:
            x -= (sprite.w - config.TILE_SIZE) // 2
            y -= (sprite.h - config.TILE_SIZE) // 2
        if colkey is None:
            pyxel.blt(x, y, sprite.bank, u, sprite.v, sprite.w, sprite.h)
        else:
            pyxel.blt(x, y, sprite.bank, u, sprite.v, sprite.w, sprite.h, colkey)
