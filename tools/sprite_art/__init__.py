"""仮素材（16×16、ボスは32×32）のドット絵データ。tools/make_placeholder_sprites.py から使う。

1行 = 16進の文字列（1文字 = Pyxel のパレット番号、0 = 透過色）。
敵などのテンプレートでは、大文字を役割（B=体、L=明るい面、D=影、A=目や模様）、"." を透過として書き、
色は make_placeholder_sprites.py で割り当てる。小文字・数字はそのままの色として扱う。
"""

Pixels = list[str]


def shift(row: str, dx: int, fill: str = "0") -> str:
    """行を左右にずらす（はみ出した分は捨て、空いた分は fill で埋める）。"""
    if dx > 0:
        return fill * dx + row[:-dx]
    if dx < 0:
        return row[-dx:] + fill * -dx
    return row


def patch(frame: Pixels, rows: dict[int, str]) -> Pixels:
    """一部の行だけを差し替えた別のコマを作る。"""
    return [rows.get(i, row) for i, row in enumerate(frame)]
