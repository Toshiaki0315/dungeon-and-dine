"""料理カットインの背景（本素材）を描き出すスクリプト。仕様書 2.4。

    .venv/bin/python tools/make_cutin_background.py

assets/cutins/cooking_<エリアID>.png に 320×140 の背景を書き出す。
色はパレット番号で描き、既定のパレットのまま保存する（ゲーム側で料理用パレットに入れ替えるため、
番号さえ保たれていれば、読み込んだあとに正しい色で表示される）。
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

# 料理用パレット（data/palettes.json）での見え方を想定した色番号
DARK = 1  # 洞窟の奥
CAVE = 2  # 岩肌
MOSS = 3  # 苔
MOSS_LIGHT = 11  # 明るい苔
GROUND = 4  # 地面
STONE = 5  # 石
GLOW = 10  # 光るキノコ
PALE = 6  # 石の照り返し
WATER = 12  # 水たまり


def draw_background(image: pyxel.Image) -> None:
    """焚き火を囲む洞窟を描く。中央下は、炎や食材を重ねるために空けておく。"""
    image.cls(DARK)

    # 奥の岩肌（ディザリングで奥行きを出す）
    image.dither(0.5)
    image.rect(0, 16, WIDTH, GROUND_TOP - 16, CAVE)
    image.dither(1.0)
    image.elli(-60, -70, 220, 170, CAVE)
    image.elli(WIDTH - 160, -80, 220, 170, CAVE)
    image.elli(90, -96, 140, 150, CAVE)

    # 天井から下がる鍾乳石（細く尖らせる）
    for x, length in ((28, 14), (74, 9), (132, 18), (196, 11), (248, 20), (296, 10)):
        for i in range(length):
            half = max(0, (length - i) // 5)
            color = STONE if i >= length - 3 else CAVE
            image.rect(x - half, i, half * 2 + 1, 1, color)

    # 苔（岩の上側に散らす）
    image.dither(0.5)
    for x, y, w in ((12, 40, 46), (104, 30, 60), (214, 46, 52), (280, 34, 34)):
        image.elli(x, y, w, 10, MOSS)
    image.dither(1.0)
    for x, y in ((20, 44), (60, 42), (128, 34), (168, 36), (230, 50), (296, 38)):
        image.pset(x, y, MOSS_LIGHT)
        image.pset(x + 3, y + 2, MOSS_LIGHT)

    # 光るキノコ（苔むす洞窟らしさ）
    for x, y in ((44, 92), (262, 88)):
        image.elli(x - 4, y - 4, 9, 6, GLOW)
        image.rect(x - 1, y + 1, 2, 4, PALE)

    # 地面と石
    image.rect(0, GROUND_TOP, WIDTH, HEIGHT - GROUND_TOP, GROUND)
    image.dither(0.5)
    image.rect(0, GROUND_TOP, WIDTH, 5, STONE)
    image.dither(1.0)
    for x, y, w, h in ((24, GROUND_TOP + 14, 30, 12), (268, GROUND_TOP + 10, 36, 14)):
        image.elli(x, y, w, h, STONE)

    # 水たまり
    image.dither(0.5)
    image.elli(150, HEIGHT - 16, 60, 12, WATER)
    image.dither(1.0)


def main() -> None:
    pyxel.init(WIDTH, HEIGHT, title="make_cutin_background")
    image = pyxel.Image(WIDTH, HEIGHT)
    draw_background(image)

    config.CUTIN_DIR.mkdir(parents=True, exist_ok=True)
    path = config.CUTIN_DIR / "cooking_moss.png"
    image.save(str(path), 1)
    print(f"{path} を書き出しました（{WIDTH}×{HEIGHT}）")
    pyxel.quit()


if __name__ == "__main__":
    main()
