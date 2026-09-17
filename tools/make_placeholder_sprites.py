"""仮のドット絵素材を作るスクリプト。仕様書 2.3.1。

assets/resources.pyxres のイメージバンク0に 16×16（ボスは32×32）の仮素材を描き込み、
その位置を data/sprites.json に書き出す。ゲーム本体からは import しないこと。

    .venv/bin/python tools/make_placeholder_sprites.py

- 絵のデータは tools/sprite_art/ にある。
- 既存の resources.pyxres があれば読み込んでから描き込むので、サウンドなど他の素材は残る。
- sprites.json は上書きする。本素材に差し替えたあとは実行しないこと。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(TOOLS_DIR))

import pyxel  # noqa: E402
from sprite_art import Pixels, leo, terrain  # noqa: E402
from sprite_art.bosses import BOSSES  # noqa: E402
from sprite_art.items import ITEMS, ROTTEN_RECOLOR, TRAPS  # noqa: E402
from sprite_art.monsters import (  # noqa: E402
    CHEST_COLORS,
    LEAVES,
    MERCHANT,
    MERCHANT_SPRITE,
    MONSTERS,
    TEMPLATES,
)

from game import config  # noqa: E402


def recolor(pixels: Pixels, mapping: dict[str, int]) -> Pixels:
    table = {key: f"{value:x}" for key, value in mapping.items()}
    return ["".join(table.get(c, c) for c in row) for row in pixels]


def area_tiles() -> dict[str, list[Pixels]]:
    """floors.json のエリアごとの色で、床・壁・通路の色違いを作る（仕様書 5.6）。"""
    data = json.loads((config.DATA_DIR / "floors.json").read_text(encoding="utf-8"))
    result: dict[str, list[Pixels]] = {}
    for area in data["areas"]:
        tiles = area.get("tiles")
        if not tiles:
            continue
        ground = {"1": tiles["floor"], "5": tiles["floor_dot"]}
        wall = {"5": tiles["wall"], "1": tiles["wall_mortar"]}
        result[f"floor_{area['id']}"] = [recolor(terrain.FLOOR, ground)]
        result[f"corridor_{area['id']}"] = [recolor(terrain.CORRIDOR, ground)]
        result[f"wall_{area['id']}"] = [recolor(terrain.WALL, wall)]
    return result


def paint(template: str, body: int, accent: int, dark: int, light: int) -> Pixels:
    """テンプレートの役割（B/A/D/L）に色を割り当てる。小文字・数字はそのままの色。"""
    table = {".": "0", "B": f"{body:x}", "A": f"{accent:x}", "D": f"{dark:x}", "L": f"{light:x}"}
    return ["".join(table.get(c, c) for c in row) for row in TEMPLATES[template]]


def mirror(frames: list[Pixels]) -> list[Pixels]:
    return [[row[::-1] for row in frame] for frame in frames]


def bob(frame: Pixels) -> list[Pixels]:
    """待機の2コマ（2コマ目は1px沈む）。"""
    return [frame, ["0" * len(frame[0]), *frame[:-1]]]


def build_sheet() -> list[dict[str, list[Pixels]]]:
    """名前 → コマのリスト。行ごとに左から詰めて配置する。"""
    monsters = {name: bob(paint(*spec)) for name, spec in MONSTERS.items()}
    monsters[MERCHANT_SPRITE] = bob(paint(*MERCHANT))
    chests = {
        "chest_closed": [paint("chest_closed", *CHEST_COLORS)],
        "chest_open": [paint("chest_open", *CHEST_COLORS)],
    }
    items = {name: [paint("leaf", *colors)] for name, colors in LEAVES.items()}
    items.update({name: [pixels] for name, pixels in ITEMS.items()})
    items["item_rotten_meat"] = [recolor(ITEMS["item_meat"], ROTTEN_RECOLOR)]
    return [
        {
            "floor": [terrain.FLOOR],
            "wall": [terrain.WALL],
            "corridor": [terrain.CORRIDOR],
            "stairs_down": [terrain.STAIRS_DOWN],
            "floor_safe": [terrain.FLOOR_SAFE],
            "campfire": terrain.CAMPFIRE,
        },
        {
            "leo_down": leo.walk_down(),
            "leo_up": leo.walk_up(),
            "leo_left": mirror(leo.walk_right()),
            "leo_right": leo.walk_right(),
        },
        {**monsters, **chests},
        items,
        {name: [pixels] for name, pixels in TRAPS.items()},
        area_tiles(),
        BOSSES,
    ]


def main() -> None:
    size = config.SPRITE_SIZE  # 素材シート上の1マスの絵の大きさ（ボスはその2倍）
    pyxel.init(64, 64, title="make_placeholder_sprites")
    if config.RESOURCE_PATH.exists():
        pyxel.load(str(config.RESOURCE_PATH))

    image = pyxel.images[0]
    image.cls(0)  # 以前の配置の絵が残らないよう、描き込む前に消す
    sprites: dict[str, dict[str, int]] = {}
    v = 0
    for entries in build_sheet():
        u = 0
        row_height = 0
        for name, frames in entries.items():
            w, h = len(frames[0][0]), len(frames[0])
            width = len(frames) * w
            if u + width > image.width:
                # 1行に入りきらないので次の行へ送る（敵が増えても破綻しないようにする）
                v += row_height
                u, row_height = 0, 0
            for i, pixels in enumerate(frames):
                assert len(pixels) == h and all(len(line) == w for line in pixels), name
                image.set(u + i * w, v, pixels)
            entry = {"u": u, "v": v, "frames": len(frames)}
            if (w, h) != (size, size):
                entry.update({"w": w, "h": h})
            sprites[name] = entry
            u += width
            row_height = max(row_height, h)
        v += row_height
    assert v <= image.height, f"素材シートの高さ（{image.height}px）を超えています: {v}px"

    config.RESOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    pyxel.save(str(config.RESOURCE_PATH))

    sprites_json = {"version": 1, "tile_size": size, "image_bank": 0, "sprites": sprites}
    (config.DATA_DIR / "sprites.json").write_text(
        json.dumps(sprites_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{config.RESOURCE_PATH} と data/sprites.json を更新しました（{len(sprites)} 件、{v}px）")
    pyxel.quit()


if __name__ == "__main__":
    main()
