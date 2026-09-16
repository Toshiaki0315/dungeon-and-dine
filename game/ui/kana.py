"""名前入力の五十音表。仕様書 6.1。

表の中身とカーソル移動だけを持ち、描画は ui/name_input_view.py（シーン側）が行う。
pyxel を import しないこと（テストしやすくするため）。
"""

from __future__ import annotations

Grid = tuple[tuple[str, ...], ...]  # 行 × 列。空欄は "" で表す

PAGE_HIRAGANA = "ひらがな"
PAGE_KATAKANA = "カタカナ"
PAGE_ALNUM = "英数"


def _pairs(plain: str, marked: str) -> dict[str, str]:
    return dict(zip(plain, marked, strict=True))


# 濁点・半濁点（「゛」「゜」を選ぶと、直前の1文字を変換する）


VOICED: dict[str, str] = {
    **_pairs("かきくけこさしすせそ", "がぎぐげござじずぜぞ"),
    **_pairs("たちつてとはひふへほ", "だぢづでどばびぶべぼ"),
    **_pairs("カキクケコサシスセソ", "ガギグゲゴザジズゼゾ"),
    **_pairs("タチツテトハヒフヘホ", "ダヂヅデドバビブベボ"),
}
SEMI_VOICED: dict[str, str] = {
    **_pairs("はひふへほ", "ぱぴぷぺぽ"),
    **_pairs("ハヒフヘホ", "パピプペポ"),
}

HIRAGANA: Grid = (
    tuple("あいうえおかきくけこ"),
    tuple("さしすせそたちつてと"),
    tuple("なにぬねのはひふへほ"),
    tuple("まみむめもやゆよらり"),
    tuple("るれろわをんーっゃゅ"),
    tuple("ょぁぃぅぇぉ　　　　"),
)
KATAKANA: Grid = (
    tuple("アイウエオカキクケコ"),
    tuple("サシスセソタチツテト"),
    tuple("ナニヌネノハヒフヘホ"),
    tuple("マミムメモヤユヨラリ"),
    tuple("ルレロワヲンーッャュ"),
    tuple("ョァィゥェォ　　　　"),
)
ALNUM: Grid = (
    tuple("ABCDEFGHIJ"),
    tuple("KLMNOPQRST"),
    tuple("UVWXYZ0123"),
    tuple("456789abcd"),
    tuple("efghijklmn"),
    tuple("opqrstuvwxyz"[:10]),
)

PAGES: tuple[tuple[str, Grid], ...] = (
    (PAGE_HIRAGANA, HIRAGANA),
    (PAGE_KATAKANA, KATAKANA),
    (PAGE_ALNUM, ALNUM),
)

FULL_WIDTH_SPACE = "　"


def grid_for(page: int) -> Grid:
    return PAGES[page % len(PAGES)][1]


def page_name(page: int) -> str:
    return PAGES[page % len(PAGES)][0]


def char_at(grid: Grid, row: int, column: int) -> str:
    """その位置の文字。空欄なら空文字を返す。"""
    if not 0 <= row < len(grid) or not 0 <= column < len(grid[row]):
        return ""
    char = grid[row][column]
    return "" if char == FULL_WIDTH_SPACE else char


def move(grid: Grid, row: int, column: int, dx: int, dy: int) -> tuple[int, int]:
    """カーソルを動かす。端は反対側へ回り込む。"""
    rows = len(grid)
    columns = len(grid[0])
    return ((row + dy) % rows, (column + dx) % columns)


def voiced(char: str) -> str | None:
    """濁点を付けた文字。付けられなければ None。"""
    return VOICED.get(char)


def semi_voiced(char: str) -> str | None:
    """半濁点を付けた文字。付けられなければ None。"""
    return SEMI_VOICED.get(char)


def apply_mark(text: str, *, semi: bool = False) -> str:
    """末尾の1文字に濁点（または半濁点）を付ける。付けられないときはそのまま返す。"""
    if not text:
        return text
    converted = semi_voiced(text[-1]) if semi else voiced(text[-1])
    return text[:-1] + converted if converted is not None else text
