"""仮のドット絵素材を作るスクリプト。仕様書 2.3.1。

assets/resources.pyxres のイメージバンク0に 8×8 の仮素材を描き込み、
その位置を data/sprites.json に書き出す。ゲーム本体からは import しないこと。

    .venv/bin/python tools/make_placeholder_sprites.py

- 既存の resources.pyxres があれば読み込んでから描き込むので、サウンドなど他の素材は残る。
- sprites.json は上書きする。本素材に差し替えたあとは実行しないこと。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pyxel  # noqa: E402

from game import config  # noqa: E402

Pixels = list[str]  # 8行の16進文字列（1文字 = Pyxel のパレット番号、0 = 透過色）

# --- 地形 ---
FLOOR: Pixels = [
    "11111111",
    "11111111",
    "11511111",
    "11111111",
    "11111151",
    "11111111",
    "15111111",
    "11111111",
]
WALL: Pixels = [
    "55515555",
    "55515555",
    "55515555",
    "11111111",
    "55555551",
    "55555551",
    "55555551",
    "11111111",
]
CORRIDOR: Pixels = [
    "11111111",
    "10111111",
    "11111011",
    "11511111",
    "11111111",
    "11110111",
    "10111151",
    "11111111",
]
STAIRS_DOWN: Pixels = [
    "11111111",
    "17777771",
    "10000001",
    "11dddd11",
    "10000001",
    "11155111",
    "10000001",
    "11111111",
]

# --- レオ（茶色の髪、緑のスカーフ、革の鎧） ---
LEO_DOWN: list[Pixels] = [
    [
        "00444400",
        "04ffff40",
        "0f1ff1f0",
        "00bbbb00",
        "0f9449f0",
        "00944900",
        "00500500",
        "00500500",
    ],
    [
        "00444400",
        "04ffff40",
        "0f1ff1f0",
        "00bbbb00",
        "0f9449f0",
        "00944900",
        "00500500",
        "05000050",
    ],
]
LEO_UP: list[Pixels] = [
    [
        "00444400",
        "04444440",
        "04444440",
        "00bbbb00",
        "0f9999f0",
        "00999900",
        "00500500",
        "00500500",
    ],
    [
        "00444400",
        "04444440",
        "04444440",
        "00bbbb00",
        "0f9999f0",
        "00999900",
        "00500500",
        "05000050",
    ],
]
LEO_RIGHT: list[Pixels] = [
    [
        "00444400",
        "0444fff0",
        "0444f1f0",
        "00bbbb00",
        "00949f00",
        "00944900",
        "00500500",
        "00500500",
    ],
    [
        "00444400",
        "0444fff0",
        "0444f1f0",
        "00bbbb00",
        "00949f00",
        "00944900",
        "00500500",
        "05000050",
    ],
]


def mirror(frames: list[Pixels]) -> list[Pixels]:
    return [[row[::-1] for row in frame] for frame in frames]


# 名前 → コマのリスト。行ごとに左から詰めて配置する。
SHEET: list[dict[str, list[Pixels]]] = [
    {"floor": [FLOOR], "wall": [WALL], "corridor": [CORRIDOR], "stairs_down": [STAIRS_DOWN]},
    {
        "leo_down": LEO_DOWN,
        "leo_up": LEO_UP,
        "leo_left": mirror(LEO_RIGHT),
        "leo_right": LEO_RIGHT,
    },
]


def main() -> None:
    size = config.TILE_SIZE
    pyxel.init(64, 64, title="make_placeholder_sprites")
    if config.RESOURCE_PATH.exists():
        pyxel.load(str(config.RESOURCE_PATH))

    image = pyxel.images[0]
    sprites: dict[str, dict[str, int]] = {}
    for row, entries in enumerate(SHEET):
        u = 0
        v = row * size
        for name, frames in entries.items():
            for i, pixels in enumerate(frames):
                assert len(pixels) == size and all(len(line) == size for line in pixels), name
                image.set(u + i * size, v, pixels)
            sprites[name] = {"u": u, "v": v, "frames": len(frames)}
            u += len(frames) * size

    config.RESOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    pyxel.save(str(config.RESOURCE_PATH))

    sprites_json = {"version": 1, "tile_size": size, "image_bank": 0, "sprites": sprites}
    (config.DATA_DIR / "sprites.json").write_text(
        json.dumps(sprites_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{config.RESOURCE_PATH} と data/sprites.json を更新しました（{len(sprites)} 件）")
    pyxel.quit()


if __name__ == "__main__":
    main()
