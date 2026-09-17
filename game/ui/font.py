"""日本語フォントの一元管理。仕様書 2.5。

すべての文字描画は `draw_text` を経由すること。
"""

from __future__ import annotations

import sys

import pyxel

from game import config

_font: pyxel.Font | None = None
# 文字は作業用の画像に等倍で描いてから、FONT_SCALE 倍に拡大して画面へ転送する
# （pyxel.text には拡大の引数がないため）。1フレームに60行描いても1ms未満で済む。
_scratch: pyxel.Image | None = None
MISAKI_GLYPH_HEIGHT = 8


def load() -> None:
    """美咲ゴシック第2（BDF）を読み込む。見つからなければ組み込みフォントで代用する。"""
    global _font, _scratch
    if config.FONT_PATH.exists():
        _font = pyxel.Font(str(config.FONT_PATH))
    else:
        _font = None
        print(
            f"[font] {config.FONT_PATH} が見つかりません。組み込みフォントで代用します。",
            file=sys.stderr,
        )
    _scratch = pyxel.Image(config.SCREEN_WIDTH, _glyph_height())


def is_japanese_available() -> bool:
    return _font is not None


def _glyph_height() -> int:
    """等倍での1文字の高さ（px）。"""
    return MISAKI_GLYPH_HEIGHT if _font is not None else pyxel.FONT_HEIGHT


def _raw_width(s: str) -> int:
    """等倍での文字列の幅（px）。"""
    if _font is not None:
        return _font.text_width(s)
    return len(s) * pyxel.FONT_WIDTH


def text_width(s: str) -> int:
    """文字列の画面上の描画幅（px）を返す。FONT_SCALE 倍に拡大したあとの幅。"""
    return _raw_width(s) * config.FONT_SCALE


def draw_text_centered(y: int, s: str, col: int) -> None:
    """画面の横中央に文字列を描画する。"""
    draw_text((config.SCREEN_WIDTH - text_width(s)) // 2, y, s, col)


def draw_text(x: int, y: int, s: str, col: int) -> None:
    """文字列を FONT_SCALE 倍に拡大して描画する。"""
    scale = config.FONT_SCALE
    if scale == 1 or _scratch is None:
        if _font is not None:
            pyxel.text(x, y, s, col, _font)
        else:
            pyxel.text(x, y, s, col)
        return
    w = min(_raw_width(s), _scratch.width)
    if w <= 0:
        return
    h = _glyph_height()
    # 作業用画像の地を透明色で塗る。
    # 文字色が透明色と同じだと文字ごと消えるので、そのときは別の色にする
    key = 1 if col == config.TRANSPARENT_COLOR else config.TRANSPARENT_COLOR
    _scratch.rect(0, 0, w, h, key)
    if _font is not None:
        _scratch.text(0, 0, s, col, _font)
    else:
        _scratch.text(0, 0, s, col)
    # pyxel.blt の scale は中心を基準に拡大するので、左上が (x, y) に来るようずらす
    bx = x + w * (scale - 1) // 2
    by = y + h * (scale - 1) // 2
    pyxel.blt(bx, by, _scratch, 0, 0, w, h, key, scale=scale)
