"""ボス（32×32、2コマ）。仕様書 2.3.1 / 8.3。

32×32 は1行ずつ文字で書くと数え間違いやすいので、円・多角形・線を重ねて描く。
20階ごとのボスは、色だけでなく輪郭（丸い口・王冠の頭蓋・岩塊・翼・菱形）で見分けられるようにする。
体の色は、ボス階の床の色（1）と床の点の色（2）を主にしない（背景に沈むため）。
"""

from __future__ import annotations

from sprite_art import Pixels

SIZE = 32


class Canvas:
    """16色の番号で塗る 32×32 の画用紙。0 は透過。"""

    def __init__(self) -> None:
        self.cells = [[0] * SIZE for _ in range(SIZE)]

    def set(self, x: int, y: int, color: int) -> None:
        if 0 <= x < SIZE and 0 <= y < SIZE:
            self.cells[y][x] = color

    def get(self, x: int, y: int) -> int:
        return self.cells[y][x] if 0 <= x < SIZE and 0 <= y < SIZE else 0

    def rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.set(i, j, color)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, color: int) -> None:
        """塗りつぶした楕円。中心はドットの境目（例: 15.5）にも置ける。"""
        for j in range(SIZE):
            for i in range(SIZE):
                dx, dy = (i - cx) / rx, (j - cy) / ry
                if dx * dx + dy * dy <= 1.0:
                    self.set(i, j, color)

    def polygon(self, points: list[tuple[float, float]], color: int) -> None:
        """塗りつぶした多角形（ドットの中心が内側にあれば塗る）。"""
        for j in range(SIZE):
            for i in range(SIZE):
                if _inside(i, j, points):
                    self.set(i, j, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            self.set(round(x0 + (x1 - x0) * s / steps), round(y0 + (y1 - y0) * s / steps), color)

    def recolor_where(self, predicate, color: int) -> None:  # noqa: ANN001
        for j in range(SIZE):
            for i in range(SIZE):
                if self.cells[j][i] and predicate(i, j, self.cells[j][i]):
                    self.cells[j][i] = color

    def mirror_left_to_right(self) -> None:
        """左半分を右半分へ写す（左右対称の絵）。"""
        for row in self.cells:
            for i in range(SIZE // 2):
                row[SIZE - 1 - i] = row[i]

    def pixels(self) -> Pixels:
        return ["".join(f"{c:x}" for c in row) for row in self.cells]


def _inside(x: float, y: float, points: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(points)
    for k in range(n):
        (x0, y0), (x1, y1) = points[k], points[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


# --- B20F「奈落の大喰らい」: 丸い体いっぱいの口。2コマ目は口を大きく開ける ---
def devourer(frame: int) -> Pixels:
    c = Canvas()
    body, shade, light = 8, 2, 14
    # 頭の上のとげ
    for x in (8, 15, 22):
        c.polygon([(x - 1, 6), (x + 3, 6), (x + 1, 0)], shade)
    c.ellipse(15.5, 17, 15, 14.5, body)
    c.recolor_where(lambda i, j, _: (i - 11) ** 2 + (j - 10) ** 2 > 20**2, shade)  # 右下の影
    c.ellipse(4.5, 15, 1.2, 3, light)  # 左側の照り
    # 目（黄色に黒い瞳）
    for ex in (10, 21):
        c.ellipse(ex, 10, 3.2, 2.6, 10)
        c.rect(ex, 10, 1, 2, 1)
    # 口（2コマ目は上下に広がる）
    mouth_h = 5.5 if frame == 0 else 8
    c.ellipse(15.5, 21, 12, mouth_h, 1)
    top = round(21 - mouth_h)
    bottom = round(21 + mouth_h)
    for x in range(5, 27, 3):  # 上の歯
        c.polygon([(x, top + 1), (x + 3, top + 1), (x + 1.5, top + 4)], 7)
    for x in range(6, 26, 3):  # 下の歯
        c.polygon([(x, bottom), (x + 3, bottom), (x + 1.5, bottom - 3)], 7)
    c.ellipse(15.5, bottom - 2.5, 5, 1.8, 14)  # 舌
    return c.pixels()


# --- B40F「骸骨王」: 王冠を頂く頭蓋と、肩の骨。2コマ目は顎が開く ---
def bone_sovereign(frame: int) -> Pixels:
    c = Canvas()
    bone, shade, gold, gem = 7, 13, 10, 8
    # 肩の骨とマント
    c.polygon([(1, 31), (6, 22), (26, 22), (31, 31)], 12)
    c.ellipse(5, 23, 4, 2.5, bone)
    c.ellipse(26, 23, 4, 2.5, bone)
    # 頭蓋
    c.ellipse(15.5, 14, 11.5, 10, bone)
    c.recolor_where(lambda i, j, v: v == bone and j >= 19 and j < 24 and (i < 8 or i > 23), shade)
    c.rect(7, 10, 2, 1, 6)  # 照り（淡い青）
    c.rect(6, 11, 1, 2, 6)
    # 眼窩と光る瞳
    for ex in (10.5, 20.5):
        c.ellipse(ex, 15, 3.6, 3.2, 1)
        c.ellipse(ex, 15.5, 1.2, 1.2, gem)
    c.polygon([(14.5, 21), (17.5, 21), (16, 18)], 1)  # 鼻
    # 顎（2コマ目は3ドット下がり、口の中の闇が見える）
    drop = 0 if frame == 0 else 3
    if drop:
        c.rect(9, 23, 14, drop, 1)
    c.rect(9, 23 + drop, 14, 5, bone)
    c.rect(9, 27 + drop, 14, 1, shade)
    for x in range(10, 22, 2):  # 歯の隙間
        c.rect(x, 23 + drop, 1, 2, shade)
    # 王冠（5本の角と宝石）
    c.rect(6, 5, 20, 3, gold)
    for x in (6, 11, 16, 21, 25):
        c.polygon([(x - 0.5, 5.5), (x + 1.5, 5.5), (x + 0.5, 0)], gold)
    c.rect(6, 7, 20, 1, 9)
    for x in (9, 15.5, 22):
        c.ellipse(x, 6, 1, 0.8, gem)
    return c.pixels()


ROCK_GRIT = ((4, 16), (28, 18), (10, 14), (21, 13), (18, 19), (3, 21), (27, 22), (11, 27), (20, 27))


# --- B60F「溶岩の暴君」: 角の生えた岩塊。溶岩の割れ目が走る。2コマ目は割れ目が燃え上がる ---
def magma_tyrant(frame: int) -> Pixels:
    c = Canvas()
    rock, dark, edge = 4, 2, 15
    lava = 10 if frame == 0 else 7
    lava_edge = 9 if frame == 0 else 10
    # 角
    c.polygon([(6, 1), (10, 6), (7, 8)], 13)
    c.polygon([(25, 1), (21, 6), (24, 8)], 13)
    # 頭・肩・腕・脚（矩形を積んで角を立てる）
    c.rect(9, 3, 14, 10, rock)
    c.rect(2, 11, 28, 11, rock)
    c.rect(0, 13, 6, 12, rock)
    c.rect(26, 13, 6, 12, rock)
    c.rect(0, 24, 7, 5, dark)  # 拳
    c.rect(25, 24, 7, 5, dark)
    c.rect(7, 21, 18, 4, rock)
    c.rect(7, 25, 7, 7, rock)
    c.rect(18, 25, 7, 7, rock)
    c.rect(6, 30, 8, 2, dark)
    c.rect(18, 30, 8, 2, dark)
    # 上側の縁を明るく、下側を暗く
    c.recolor_where(lambda i, j, v: v == rock and c.get(i, j - 1) == 0, edge)
    c.recolor_where(lambda i, j, v: v == rock and c.get(i, j + 1) == 0, dark)
    # 岩肌のざらつき
    for x, y in ROCK_GRIT:
        if c.get(x, y) == rock:
            c.set(x, y, dark)
    # 目（燃える目）
    c.rect(11, 7, 3, 2, lava)
    c.rect(18, 7, 3, 2, lava)
    c.rect(13, 11, 6, 1, 8)  # 口
    # 溶岩の割れ目
    cracks = [
        [(15, 13), (13, 16), (15, 18), (12, 22)],
        [(5, 14), (8, 17), (6, 20)],
        [(26, 14), (23, 17), (25, 21)],
        [(10, 25), (11, 29)],
        [(21, 25), (20, 29)],
    ]
    for points in cracks:
        for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
            c.line(x0, y0, x1, y1, lava)
    if frame == 1:
        c.recolor_where(
            lambda i, j, v: (
                v in (rock, edge, dark)
                and any(
                    c.get(i + dx, j + dy) == lava for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                )
            ),
            lava_edge,
        )
    return c.pixels()


# --- B80F「虚無の熾天使」: 光輪と、上下3対の翼。2コマ目は翼を下ろす ---
def void_seraph(frame: int) -> Pixels:
    c = Canvas()
    wing, feather, robe, robe_shade = 12, 6, 7, 13
    lift = 0 if frame == 0 else 3
    # 翼（左半分だけ描いて、あとで右へ写す）
    c.polygon([(13, 11), (0, 1 + lift), (3, 9 + lift), (1, 12 + lift), (12, 15)], wing)
    c.polygon([(13, 14), (0, 16 + lift), (3, 19 + lift), (1, 23 + lift), (13, 19)], wing)
    c.polygon([(13, 19), (4, 27 + lift), (7, 29 + lift), (14, 23)], wing)
    for x0, y0, x1, y1 in ((12, 12, 2, 3 + lift), (12, 16, 2, 18 + lift), (13, 20, 6, 27 + lift)):
        c.line(x0, y0, x1, y1, feather)
    c.mirror_left_to_right()
    # 胴（縦長の衣）と頭
    c.polygon([(16, 10), (11, 31), (21, 31)], robe)
    c.polygon([(15.5, 10), (13, 22), (16, 31), (16, 10)], robe)
    c.recolor_where(lambda i, j, v: v == robe and i >= 18, robe_shade)
    c.ellipse(15.5, 8, 3.5, 3.5, robe)
    c.ellipse(15.5, 8.5, 2.2, 2.4, 1)  # 顔は虚無（暗い）
    c.rect(15, 8, 2, 2, 8)  # 一つ目
    c.ellipse(15.5, 17, 1.6, 1.6, 8)  # 胸の宝玉
    # 光輪
    c.ellipse(15.5, 2.5, 6, 2, 10)
    c.ellipse(15.5, 2.5, 4, 1, 0)
    return c.pixels()


# --- B100F「迷宮の造り主」: 菱形の幾何学体。内部の迷路と目。2コマ目は迷路が回り、目を細める ---
def labyrinth_maker(frame: int) -> Pixels:
    c = Canvas()
    rim, face, wall, eye = 10, 7, 9, 8

    def dist(i: int, j: int) -> float:
        return abs(i - 15.5) + abs(j - 15.5)

    for j in range(SIZE):
        for i in range(SIZE):
            d = dist(i, j)
            if d <= 15.5:
                c.set(i, j, rim if d > 13 else face)
    # 内側の迷路（菱形の輪に切れ目。2コマ目は切れ目の位置が90度回る）
    for ring, gaps in ((10.5, ((0, -1), (0, 1))), (6.5, ((-1, 0), (1, 0)))):
        if frame == 1:
            gaps = tuple((-gy, gx) for gx, gy in gaps)
        for j in range(SIZE):
            for i in range(SIZE):
                if abs(dist(i, j) - ring) <= 0.5:
                    dx, dy = i - 15.5, j - 15.5
                    blocked = any(
                        dx * gx + dy * gy > 0 and abs(dx * gy - dy * gx) < 2 for gx, gy in gaps
                    )
                    if not blocked:
                        c.set(i, j, wall)
    # 迷路の仕切り（輪と輪をつなぐ短い壁）
    spokes = (
        ((15, 6), (16, 25), (6, 16), (25, 15))
        if frame == 0
        else ((6, 15), (25, 16), (15, 25), (16, 6))
    )
    for x, y in spokes:
        c.rect(x, y, 1, 1, wall)
    # 目
    c.ellipse(15.5, 15.5, 4, 2.6 if frame == 0 else 1.2, eye)
    c.rect(15, 15, 2, 2 if frame == 0 else 1, 1)
    # 照り
    for i, j in ((15, 3), (14, 4), (15, 4)):
        c.set(i, j, 7 if c.get(i, j) == rim else 6)
    return c.pixels()


BOSSES: dict[str, list[Pixels]] = {
    name: [draw(0), draw(1)]
    for name, draw in (
        ("devourer", devourer),
        ("bone_sovereign", bone_sovereign),
        ("magma_tyrant", magma_tyrant),
        ("void_seraph", void_seraph),
        ("labyrinth_maker", labyrinth_maker),
    )
}
