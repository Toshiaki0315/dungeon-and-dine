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

FLOOR_SAFE: Pixels = [
    "11111111",
    "11941111",
    "11111111",
    "14111119",
    "11111111",
    "11111141",
    "19111111",
    "11111111",
]
# 焚き火（3コマ。炎が揺れる）
CAMPFIRE: list[Pixels] = [
    [
        "00000000",
        "000a0000",
        "00a9a000",
        "0a999a00",
        "0a99990a",
        "04999940",
        "44444444",
        "04444440",
    ],
    [
        "00000000",
        "0000a000",
        "000a9a00",
        "00a99900",
        "0a99999a",
        "04999440",
        "44444444",
        "04444440",
    ],
    [
        "00000000",
        "00a00000",
        "00a9a000",
        "0099a900",
        "0a999990",
        "04499940",
        "44444444",
        "04444440",
    ],
]

# --- レオ（茶色の髪、緑のスカーフ、革の鎧） ---
LEO_DOWN: Pixels = [
    "00444400",
    "04ffff40",
    "0f1ff1f0",
    "00bbbb00",
    "0f9449f0",
    "00944900",
    "00500500",
    "00500500",
]
LEO_UP: Pixels = [
    "00444400",
    "04444440",
    "04444440",
    "00bbbb00",
    "0f9999f0",
    "00999900",
    "00500500",
    "00500500",
]
LEO_RIGHT: Pixels = [
    "00444400",
    "0444fff0",
    "0444f1f0",
    "00bbbb00",
    "00949f00",
    "00944900",
    "00500500",
    "00500500",
]

# --- 敵・宝箱のテンプレート（B=体、A=目や模様、D=影や脚、"."=透過） ---
TEMPLATES: dict[str, list[str]] = {
    "blob": [
        "........",
        "...BB...",
        "..BBBB..",
        ".BBBBBB.",
        ".BABBAB.",
        ".BBBBBB.",
        "BBBBBBBB",
        ".DDDDDD.",
    ],
    "beast": [
        "........",
        "........",
        ".BB.....",
        "BABBBBB.",
        "BBBBBBBB",
        ".BBBBBBD",
        ".D.D.D..",
        "........",
    ],
    "flyer": [
        "........",
        "B......B",
        "BB.BB.BB",
        "BBBAABBB",
        ".BBBBBB.",
        "..B..B..",
        "........",
        "........",
    ],
    "mushroom": [
        "..BBBB..",
        ".BABBAB.",
        "BBBBBBBB",
        "...DD...",
        "..DAAD..",
        "..DDDD..",
        "..D..D..",
        "........",
    ],
    "humanoid": [
        "..BBBB..",
        "..ABBA..",
        "..BBBB..",
        "...BB...",
        ".BBBBBB.",
        "...BB...",
        "..B..B..",
        "..B..B..",
    ],
    "serpent": [
        "........",
        ".....BB.",
        "....BABB",
        ".BB..BB.",
        "B..B.B..",
        "B...BB..",
        ".BBB....",
        "........",
    ],
    "centipede": [
        "........",
        "........",
        "AB.B.B..",
        "BBBBBBBB",
        "BBBBBBBB",
        ".D.D.D.D",
        "D.D.D.D.",
        "........",
    ],
    "ghost": [
        "..BBBB..",
        ".BBBBBB.",
        ".BABBAB.",
        ".BBBBBB.",
        "BBBBBBBB",
        "BBBBBBBB",
        "B.BB.BB.",
        "........",
    ],
    "golem": [
        ".BBBBBB.",
        ".BABBAB.",
        ".BBBBBB.",
        "BBBBBBBB",
        "BBDBBDBB",
        "BBBBBBBB",
        ".BB..BB.",
        ".BB..BB.",
    ],
    "mimic": [
        "........",
        ".BBBBBB.",
        "BAAAAAAB",
        "BDDDDDDB",
        "BDDDDDDB",
        "BAAAAAAB",
        "BBBBBBBB",
        ".D....D.",
    ],
    "chest_closed": [
        "........",
        ".BBBBBB.",
        "BBBBBBBB",
        "DDDAADDD",
        "BBBAABBB",
        "BBBBBBBB",
        "BBBBBBBB",
        "........",
    ],
    "chest_open": [
        ".BBBBBB.",
        "BDDDDDDB",
        "BDDDDDDB",
        "DDDDDDDD",
        "BBBAABBB",
        "BBBBBBBB",
        "BBBBBBBB",
        "........",
    ],
    "leaf": [
        "........",
        ".....DD.",
        "....BBBD",
        "...BBBD.",
        "..BBBD..",
        ".DBBD...",
        ".ADD....",
        "A.......",
    ],
}

# 敵ID → (テンプレート, 体, 目や模様, 影)。同じ階に出る敵どうしは色か形で見分けられるようにする。
MONSTERS: dict[str, tuple[str, int, int, int]] = {
    "slime": ("blob", 11, 1, 3),
    "giant_rat": ("beast", 13, 8, 5),
    "cave_bat": ("flyer", 2, 8, 1),
    "mushroom_man": ("mushroom", 8, 7, 15),
    "skeleton": ("humanoid", 7, 1, 13),
    "serpent": ("serpent", 3, 10, 1),
    "fire_lizard": ("beast", 9, 10, 8),
    "mimic": ("mimic", 4, 7, 1),
    "armored_centipede": ("centipede", 5, 8, 13),
    "rock_golem": ("golem", 13, 10, 5),
    "shadow_wraith": ("ghost", 2, 8, 1),
    "labyrinth_hound": ("beast", 4, 8, 2),
}

# --- アイテム・武器 ---
ITEMS: dict[str, Pixels] = {
    "item_ration": [
        "00000000",
        "00000000",
        "00999900",
        "09ffff90",
        "9ffffff9",
        "94444449",
        "04444440",
        "00000000",
    ],
    "item_stove": [
        "00000000",
        "00080800",
        "00898980",
        "0dddddd0",
        "0d1111d0",
        "0dddddd0",
        "0d0000d0",
        "00000000",
    ],
    "item_loupe": [
        "00000000",
        "00ddd000",
        "0d666d00",
        "0d666d00",
        "0d666d00",
        "00ddd400",
        "00000440",
        "00000044",
    ],
    "item_scroll": [
        "00000000",
        "04444440",
        "00ffff00",
        "00f11f00",
        "00ffff00",
        "00f11f00",
        "04444440",
        "00000000",
    ],
    "item_holy_water": [
        "00044000",
        "00066000",
        "00066000",
        "06cccc60",
        "6cc7ccc6",
        "6cccccc6",
        "06cccc60",
        "00666600",
    ],
    "item_arrow": [
        "00000000",
        "00000770",
        "00000470",
        "00004000",
        "00040000",
        "00400000",
        "07400000",
        "07000000",
    ],
    "item_memo": [
        "00000000",
        "0ffffff0",
        "0f1111f0",
        "0ffffff0",
        "0f111ff0",
        "0ffffff0",
        "0f11fff0",
        "0ffffff0",
    ],
    "item_gold": [
        "00000000",
        "00000000",
        "00aaaa00",
        "0a9aa9a0",
        "00aaaa00",
        "0a9aa9a0",
        "00aaaa00",
        "00000000",
    ],
    "armor_shield": [
        "00000000",
        "0dddddd0",
        "0d4444d0",
        "0d4aa4d0",
        "0d4aa4d0",
        "0d4444d0",
        "00d44d00",
        "000dd000",
    ],
    "armor_helmet": [
        "00000000",
        "000dd000",
        "00dddd00",
        "0dddddd0",
        "0d5555d0",
        "0d0000d0",
        "0d0000d0",
        "00000000",
    ],
    "armor_body": [
        "00000000",
        "04400440",
        "04444440",
        "00499400",
        "00444400",
        "00444400",
        "00444400",
        "00000000",
    ],
    "armor_shoes": [
        "00000000",
        "00000000",
        "04400000",
        "04400000",
        "04400440",
        "04444440",
        "04444440",
        "00000000",
    ],
    "weapon_knife": [
        "00000000",
        "00000070",
        "00000760",
        "00007600",
        "00076000",
        "00440000",
        "04400000",
        "00000000",
    ],
    "weapon_spear": [
        "00000077",
        "00000076",
        "00000440",
        "00004400",
        "00044000",
        "00440000",
        "04400000",
        "44000000",
    ],
    "weapon_whip": [
        "00000000",
        "00444400",
        "04000040",
        "00000040",
        "00004400",
        "00040000",
        "00400000",
        "0dd00000",
    ],
    "weapon_bow": [
        "00440000",
        "00047000",
        "00004700",
        "00004070",
        "00004700",
        "00047000",
        "00440000",
        "00000000",
    ],
    "item_meat": [
        "00000000",
        "000ee000",
        "00eeee80",
        "0eeeeee0",
        "0e8eeee0",
        "00eeee00",
        "0077e000",
        "00770000",
    ],
    "item_grilled_meat": [
        "00000000",
        "00009940",
        "000994a0",
        "00994900",
        "09949000",
        "49940000",
        "44000000",
        "00000000",
    ],
    "item_rotten_meat": [
        "00000000",
        "00033000",
        "00333b00",
        "03b33330",
        "03333b30",
        "003b3300",
        "00773000",
        "00770000",
    ],
    "item_jelly": [
        "00000000",
        "000cc000",
        "00c77c00",
        "0cccccc0",
        "0cccccc0",
        "0ccccccc",
        "00cccc00",
        "00000000",
    ],
    "item_wing": [
        "00000000",
        "02000020",
        "22022022",
        "22222222",
        "02222220",
        "00211200",
        "00000000",
        "00000000",
    ],
    "item_mushroom": [
        "00000000",
        "000cc000",
        "00c77c00",
        "0c7cc7c0",
        "0cccccc0",
        "00c66c00",
        "00066000",
        "00000000",
    ],
    "item_bone": [
        "00000000",
        "07007000",
        "77777000",
        "07077700",
        "00077070",
        "00077777",
        "00007007",
        "00000000",
    ],
    "item_shell": [
        "00000000",
        "00dddd00",
        "0d5555d0",
        "d555555d",
        "d5d55d5d",
        "0d5555d0",
        "00dddd00",
        "00000000",
    ],
    "item_salt": [
        "00000000",
        "00070000",
        "00767000",
        "07677600",
        "07667000",
        "00766700",
        "00067000",
        "00000000",
    ],
    "item_essence": [
        "00000000",
        "00022000",
        "00222200",
        "02222220",
        "022c2220",
        "02222220",
        "00222200",
        "00000000",
    ],
    "item_dish": [
        "00000000",
        "00000000",
        "00099000",
        "009aa900",
        "06699660",
        "76666667",
        "07777770",
        "00000000",
    ],
    "item_mystery": [
        "00000000",
        "00021000",
        "002e2100",
        "02122210",
        "021e2120",
        "02212210",
        "00222100",
        "00000000",
    ],
    "weapon_katana": [
        "00000007",
        "00000076",
        "00000760",
        "00007600",
        "00076000",
        "000a0000",
        "00a10000",
        "01000000",
    ],
}
LEAVES: dict[str, tuple[int, int, int]] = {
    "item_herb": (11, 4, 3),
    "item_mana_herb": (12, 4, 5),
    "item_antidote": (14, 4, 2),
}

# --- 罠（発見後に床の上へ重ねて描く） ---
TRAPS: dict[str, Pixels] = {
    "trap_pit": [
        "00000000",
        "00dddd00",
        "0d5555d0",
        "0d5555d0",
        "0d5555d0",
        "0d5555d0",
        "00dddd00",
        "00000000",
    ],
    "trap_poison_arrow": [
        "00000000",
        "0000e000",
        "000eee00",
        "0000e000",
        "0000e000",
        "0000e000",
        "000e0e00",
        "00000000",
    ],
    "trap_sleep_gas": [
        "00000000",
        "00066000",
        "06666600",
        "66666660",
        "06666600",
        "00000770",
        "00000070",
        "00000770",
    ],
    "trap_warp": [
        "00000000",
        "00cccc00",
        "0c0000c0",
        "0c0cc0c0",
        "0c0c00c0",
        "0c0ccc00",
        "00c00000",
        "00000000",
    ],
    "trap_hunger": [
        "00000000",
        "00000000",
        "09999990",
        "90000009",
        "09000090",
        "00999900",
        "00000000",
        "00000000",
    ],
    "trap_rust": [
        "00000000",
        "00940000",
        "09449000",
        "00490940",
        "00004490",
        "00094900",
        "00009000",
        "00000000",
    ],
    "trap_alarm": [
        "00000000",
        "000aa000",
        "00aaaa00",
        "00aaaa00",
        "00aaaa00",
        "0aaaaaa0",
        "000aa000",
        "00000000",
    ],
}


def paint(template: str, body: int, accent: int, dark: int) -> Pixels:
    table = {".": "0", "B": f"{body:x}", "A": f"{accent:x}", "D": f"{dark:x}"}
    return ["".join(table[c] for c in row) for row in TEMPLATES[template]]


def mirror(frames: list[Pixels]) -> list[Pixels]:
    return [[row[::-1] for row in frame] for frame in frames]


def walk(frame: Pixels) -> list[Pixels]:
    """待機・歩行の2コマ（2コマ目は足を開く）。"""
    return [frame, [*frame[:-1], "05000050"]]


def bob(frame: Pixels) -> list[Pixels]:
    """待機の2コマ（2コマ目は1px沈む）。"""
    return [frame, ["00000000", *frame[:-1]]]


def build_sheet() -> list[dict[str, list[Pixels]]]:
    """名前 → コマのリスト。行ごとに左から詰めて配置する。"""
    monsters = {name: bob(paint(*spec)) for name, spec in MONSTERS.items()}
    chests = {
        "chest_closed": [paint("chest_closed", 4, 10, 1)],
        "chest_open": [paint("chest_open", 4, 10, 1)],
    }
    items = {name: [paint("leaf", *colors)] for name, colors in LEAVES.items()}
    items.update({name: [pixels] for name, pixels in ITEMS.items()})
    return [
        {
            "floor": [FLOOR],
            "wall": [WALL],
            "corridor": [CORRIDOR],
            "stairs_down": [STAIRS_DOWN],
            "floor_safe": [FLOOR_SAFE],
            "campfire": CAMPFIRE,
        },
        {
            "leo_down": walk(LEO_DOWN),
            "leo_up": walk(LEO_UP),
            "leo_left": mirror(walk(LEO_RIGHT)),
            "leo_right": walk(LEO_RIGHT),
        },
        {**monsters, **chests},
        items,
        {name: [pixels] for name, pixels in TRAPS.items()},
    ]


def main() -> None:
    size = config.TILE_SIZE
    pyxel.init(64, 64, title="make_placeholder_sprites")
    if config.RESOURCE_PATH.exists():
        pyxel.load(str(config.RESOURCE_PATH))

    image = pyxel.images[0]
    sprites: dict[str, dict[str, int]] = {}
    for row, entries in enumerate(build_sheet()):
        u = 0
        v = row * size
        for name, frames in entries.items():
            for i, pixels in enumerate(frames):
                assert len(pixels) == size and all(len(line) == size for line in pixels), name
                image.set(u + i * size, v, pixels)
            sprites[name] = {"u": u, "v": v, "frames": len(frames)}
            u += len(frames) * size
        assert u <= image.width, f"{row} 行目が画像の幅を超えています"

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
