"""料理カットインの背景（本素材）を描き出すスクリプト。仕様書 2.4。

    .venv/bin/python tools/make_cutin_background.py

assets/cutins/cooking_<エリアID>.png に 320×140 の背景を書き出す（エリアの数だけ）。
色はパレット番号で描き、既定のパレットのまま保存する（ゲーム側でエリアごとの料理用パレットに
入れ替えるため、番号さえ保たれていれば、読み込んだあとに正しい色で表示される）。
ゲーム本体からは import しないこと。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pyxel  # noqa: E402

from game import config  # noqa: E402

# カットインの背景（仕様書 2.4）。等倍の素材の大きさで作る。画面の大きさとは別で、
# ゲーム側（ui/cooking_cutin.py）が ART_SCALE 倍に拡大して描く。
# config.SCREEN_WIDTH から決めると、画面を広げたときに下の座標のまま絵の幅だけ変わって構図が崩れる。
WIDTH, HEIGHT = 320, 140
GROUND_TOP = 104

# 料理用パレット（data/palettes.json）での色番号。エリアごとにパレットを入れ替えるので、
# 番号の意味（暗がり・岩肌・地面……）はどのエリアでも同じにしておく。
DARK = 1  # 洞窟の奥
CAVE = 2  # 岩肌
MID = 3  # 中間色（苔・石積み・鉱脈・靄）
GROUND = 4  # 地面
STONE = 5  # 石
PALE = 6  # 照り返し
WHITE = 7  # 骨・結晶の白
RED = 8
FIRE = 9
GLOW = 10  # 光るもの（キノコ・溶岩・結晶）
ACCENT = 11  # エリアごとのアクセント
BLUE = 12  # 水たまり・影
GRAY = 13


def cave_shape(image: pyxel.Image) -> None:
    """どのエリアにも共通の、洞窟の輪郭と地面。中央下は炎を重ねるので空けておく。"""
    image.cls(DARK)
    image.dither(0.5)
    image.rect(0, 16, WIDTH, GROUND_TOP - 16, CAVE)
    image.dither(1.0)
    image.elli(-60, -70, 220, 170, CAVE)
    image.elli(WIDTH - 160, -80, 220, 170, CAVE)
    image.elli(90, -96, 140, 150, CAVE)
    image.rect(0, GROUND_TOP, WIDTH, HEIGHT - GROUND_TOP, GROUND)
    image.dither(0.5)
    image.rect(0, GROUND_TOP, WIDTH, 5, STONE)
    image.dither(1.0)


def stalactites(image: pyxel.Image, tip: int = STONE) -> None:
    """天井から下がる鍾乳石（細く尖らせる）。"""
    for x, length in ((28, 14), (74, 9), (132, 18), (196, 11), (248, 20), (296, 10)):
        for i in range(length):
            half = max(0, (length - i) // 5)
            color = tip if i >= length - 3 else CAVE
            image.rect(x - half, i, half * 2 + 1, 1, color)


def stones(image: pyxel.Image) -> None:
    for x, y, w, h in ((24, GROUND_TOP + 14, 30, 12), (268, GROUND_TOP + 10, 36, 14)):
        image.elli(x, y, w, h, STONE)


def draw_moss(image: pyxel.Image) -> None:
    """苔むす洞窟（B1F〜）。苔と光るキノコ、水たまり。"""
    cave_shape(image)
    stalactites(image)
    image.dither(0.5)
    for x, y, w in ((12, 40, 46), (104, 30, 60), (214, 46, 52), (280, 34, 34)):
        image.elli(x, y, w, 10, MID)
    image.dither(1.0)
    for x, y in ((20, 44), (60, 42), (128, 34), (168, 36), (230, 50), (296, 38)):
        image.pset(x, y, ACCENT)
        image.pset(x + 3, y + 2, ACCENT)
    for x, y in ((44, 92), (262, 88)):  # 光るキノコ
        image.elli(x - 4, y - 4, 9, 6, GLOW)
        image.rect(x - 1, y + 1, 2, 4, PALE)
    stones(image)
    image.dither(0.5)
    image.elli(150, HEIGHT - 16, 60, 12, BLUE)
    image.dither(1.0)


def draw_catacomb(image: pyxel.Image) -> None:
    """骸骨の地下墓地（B6F〜）。石積みの壁、壁龕に並ぶ頭蓋骨、床に散る骨。"""
    cave_shape(image)
    # 奥の石積み（横長の石を段違いに積む）
    for row in range(5):
        y = 24 + row * 14
        offset = 0 if row % 2 == 0 else 20
        for x in range(-offset, WIDTH, 40):
            image.rect(x + 1, y + 1, 38, 12, MID)
            image.dither(0.5)
            image.rect(x + 1, y + 1, 38, 3, STONE)
            image.dither(1.0)
    # 壁龕（アーチ）と、そこに置かれた頭蓋骨
    for cx in (52, 268):
        image.rect(cx - 18, 40, 36, 44, DARK)
        image.elli(cx - 18, 26, 36, 32, DARK)
        image.elli(cx - 9, 52, 18, 16, WHITE)  # 頭蓋
        image.rect(cx - 7, 66, 14, 8, WHITE)  # 顎
        image.rect(cx - 6, 58, 4, 4, DARK)  # 眼窩
        image.rect(cx + 2, 58, 4, 4, DARK)
        for i in range(3):
            image.rect(cx - 5 + i * 4, 66, 2, 6, CAVE)
    stalactites(image, tip=WHITE)
    stones(image)
    # 床に散らばる骨
    for x, y in ((36, 124), (92, 132), (232, 126), (292, 134)):
        image.rect(x, y, 16, 2, WHITE)
        image.rect(x - 2, y - 2, 4, 6, WHITE)
        image.rect(x + 14, y - 2, 4, 6, WHITE)
    image.elli(196, 126, 18, 10, WHITE)  # 転がった頭蓋
    image.rect(200, 130, 3, 3, DARK)
    image.rect(206, 130, 3, 3, DARK)


def draw_mine(image: pyxel.Image) -> None:
    """灼熱の坑道（B11F〜）。木の支柱、溶岩の割れ目、壁に光る鉱脈。"""
    cave_shape(image)
    stalactites(image)
    # 木の支柱（左右に1本ずつ、上を梁でつなぐ）
    for x in (40, 264):
        image.rect(x - 6, 30, 12, GROUND_TOP - 24, GROUND)
        image.dither(0.5)
        image.rect(x - 6, 30, 4, GROUND_TOP - 24, STONE)
        image.dither(1.0)
    image.rect(28, 24, 248, 10, GROUND)
    image.dither(0.5)
    image.rect(28, 24, 248, 3, STONE)
    image.dither(1.0)
    # 壁の鉱脈（斜めに走る光）
    for sx, sy, length in ((96, 44, 26), (150, 36, 20), (214, 54, 22)):
        for i in range(length):
            image.pset(sx + i, sy + i // 3, GLOW if i % 3 else ACCENT)
    stones(image)
    # 地面の溶岩の割れ目（中央は炎を重ねるので、左右に置く）
    for x0, y0, w in ((16, 120, 70), (228, 128, 76)):
        image.dither(0.5)
        image.elli(x0 - 4, y0 - 4, w + 8, 14, RED)
        image.dither(1.0)
        for i in range(w):
            image.pset(x0 + i, y0 + (i // 6) % 3, GLOW if i % 4 else FIRE)


def draw_abyss(image: pyxel.Image) -> None:
    """影の深淵（B16F〜）。紫の霧、宙に浮かぶ結晶、足元の裂け目。"""
    cave_shape(image)
    stalactites(image, tip=ACCENT)
    # 奥に沈む霧（横に伸びる帯）
    image.dither(0.5)
    for y, h in ((34, 10), (58, 14), (82, 10)):
        image.elli(-20, y, WIDTH + 40, h, MID)
    image.dither(1.0)
    # 宙に浮かぶ結晶（菱形）
    for cx, cy, r in ((66, 56, 9), (250, 44, 7), (176, 30, 5)):
        for dy in range(-r, r + 1):
            half = r - abs(dy)
            image.rect(cx - half, cy + dy, half * 2 + 1, 1, ACCENT)
        image.rect(cx - 1, cy - r // 2, 2, r, PALE)
    # 漂う光の粒
    for x, y in ((30, 70), (108, 48), (140, 76), (208, 66), (288, 72), (232, 88)):
        image.pset(x, y, PALE)
        image.pset(x + 1, y + 1, ACCENT)
    stones(image)
    # 足元の裂け目（底が見えない）
    image.elli(20, 122, 64, 14, DARK)
    image.elli(236, 128, 70, 12, DARK)


def draw_bottom(image: pyxel.Image) -> None:
    """奈落の底（B20F）。焼けた岩、崩れた柱、地面を走る赤い光。"""
    cave_shape(image)
    stalactites(image, tip=RED)
    # 崩れた柱（左右）
    for x, top in ((30, 40), (272, 30)):
        image.rect(x - 10, top, 20, GROUND_TOP - top, MID)
        image.dither(0.5)
        image.rect(x - 10, top, 7, GROUND_TOP - top, STONE)
        image.dither(1.0)
        for y in range(top + 8, GROUND_TOP, 16):  # 石の継ぎ目
            image.rect(x - 10, y, 20, 1, DARK)
    image.rect(16, 36, 36, 6, MID)  # 折れて落ちた柱頭
    # 奥の赤い光（割れ目から漏れる）。中央は炎と食材を重ねるので、左右に分けて置く
    image.dither(0.5)
    image.elli(52, 58, 72, 26, RED)
    image.elli(196, 64, 76, 24, RED)
    image.dither(1.0)
    for x0, y0, length in ((64, 70, 44), (208, 76, 48)):
        for i in range(length):
            image.pset(x0 + i, y0 + (i // 8) % 2, GLOW if i % 5 else FIRE)
    stones(image)
    # 地面の亀裂
    for x0, y0 in ((24, 126), (240, 122)):
        for i in range(56):
            image.pset(x0 + i, y0 + (i // 7) % 3, RED if i % 3 else FIRE)


AREAS = {
    "moss": draw_moss,
    "catacomb": draw_catacomb,
    "mine": draw_mine,
    "abyss": draw_abyss,
    "bottom": draw_bottom,
}


def main() -> None:
    pyxel.init(WIDTH, HEIGHT, title="make_cutin_background")
    config.CUTIN_DIR.mkdir(parents=True, exist_ok=True)
    for area_id, draw in AREAS.items():
        image = pyxel.Image(WIDTH, HEIGHT)
        draw(image)
        path = config.CUTIN_DIR / f"cooking_{area_id}.png"
        image.save(str(path), 1)
        print(f"{path} を書き出しました（{WIDTH}×{HEIGHT}）")
    pyxel.quit()


if __name__ == "__main__":
    main()
