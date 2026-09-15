"""日本語フォントの一元管理。仕様書 2.5。

すべての文字描画は `draw_text` を経由すること。
"""

from __future__ import annotations

import sys

import pyxel

from game import config

_font: pyxel.Font | None = None


def load() -> None:
    """美咲ゴシック第2（BDF）を読み込む。見つからなければ組み込みフォントで代用する。"""
    global _font
    if config.FONT_PATH.exists():
        _font = pyxel.Font(str(config.FONT_PATH))
    else:
        _font = None
        print(
            f"[font] {config.FONT_PATH} が見つかりません。組み込みフォントで代用します。",
            file=sys.stderr,
        )


def is_japanese_available() -> bool:
    return _font is not None


def draw_text(x: int, y: int, s: str, col: int) -> None:
    """文字列を描画する。"""
    if _font is not None:
        pyxel.text(x, y, s, col, _font)
    else:
        pyxel.text(x, y, s, col)
