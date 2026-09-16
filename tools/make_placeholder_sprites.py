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

# ボス「奈落の大喰らい」（16×16、2コマ）。仕様書 2.3.1 / 8.3
BOSS: list[Pixels] = [
    [
        "0000888888880000",
        "0008888888888000",
        "0088822222288800",
        "0888222222228880",
        "8822aa2222aa2288",
        "8822aa2222aa2288",
        "8822222222222288",
        "8821111111111288",
        "8217777777777128",
        "8211111111111128",
        "8821777777771288",
        "8882111111112888",
        "0888222222228880",
        "0088882222888800",
        "0008888888888000",
        "0000888888880000",
    ],
    [
        "0000888888880000",
        "0008888888888000",
        "0088822222288800",
        "0888222222228880",
        "882aaa2222aaa288",
        "882aaa2222aaa288",
        "8822222222222288",
        "8811111111111188",
        "8177777777777718",
        "8111111111111118",
        "8811777777771188",
        "8811111111111188",
        "0888222222228880",
        "0088882222888800",
        "0008888888888000",
        "0000888888880000",
    ],
]

# B40F「骸骨王」（16×16、2コマ）。王冠を頂く頭蓋。2コマ目は顎が開く
BONE_SOVEREIGN: list[Pixels] = [
    [
        "000a0a0a0a0a0000",
        "000aaaaaaaaa0000",
        "0000a9a9a9a90000",
        "0007777777770000",
        "0077777777777000",
        "0770077007700700",
        "0778807780870700",
        "0778807780870700",
        "0777777777770700",
        "0777770770777700",
        "0077777777770000",
        "0007070707700000",
        "0007777777700000",
        "0000777777000000",
        "0000d0d0d0d00000",
        "00000d000d000000",
    ],
    [
        "000a0a0a0a0a0000",
        "000aaaaaaaaa0000",
        "0000a9a9a9a90000",
        "0007777777770000",
        "0077777777777000",
        "0770077007700700",
        "0778807780870700",
        "0778807780870700",
        "0777777777770700",
        "0777770770777700",
        "0077777777770000",
        "0000000000000000",
        "0007070707700000",
        "0007777777700000",
        "0000d0d0d0d00000",
        "00000d000d000000",
    ],
]

# B60F「溶岩の暴君」（16×16、2コマ）。角張った岩塊。斜めに削らず、矩形を積んで角を立てる。
# 溶岩の割れ目は黄(a)で太く通し、体色(9)との明度差で見せる。2コマ目は割れ目が広がる
MAGMA_TYRANT: list[Pixels] = [
    [
        "0099000000009900",
        "0099999999999900",
        "0099999999999900",
        "9999aa9999aa9999",
        "9999aa9999aa9999",
        "9999999999999999",
        "99999999a9999999",
        "9999999a99999999",
        "999999aa99999999",
        "9999999999999999",
        "9944999999994499",
        "9944999999994499",
        "0099999999999900",
        "0099009999009900",
        "0099009999009900",
        "0099000099000000",
    ],
    [
        "0099000000009900",
        "0099999999999900",
        "0099999999999900",
        "999aaaa99aaaa999",
        "999aaaa99aaaa999",
        "99999999a9999999",
        "9999999aa9999999",
        "999999aa99999999",
        "99999aa999999999",
        "9999aa9999999999",
        "9944aa99999a4499",
        "9944999999aa4499",
        "0099999999999900",
        "0099009999009900",
        "0099009999009900",
        "0099000099000000",
    ],
]

# B80F「虚無の熾天使」（16×16、2コマ）。翼は上下に広げ、胴との間に透明の隙間を入れて分ける。
# 胴は縦長にして、翼と別パーツだと分かる輪郭にする。2コマ目は翼を下ろす
VOID_SERAPH: list[Pixels] = [
    [
        "0cc00000000000cc",
        "0ccc000077000ccc",
        "0cccc00778000ccc",
        "0ccccc0778000ccc",
        "0cccccc77800cccc",
        "0ccccccc7880cccc",
        "00cccccc7888cccc",
        "000ccccc78888ccc",
        "000ccccc78888ccc",
        "00cccccc7888cccc",
        "0ccccccc7880cccc",
        "0cccccc77800cccc",
        "0ccccc0778000ccc",
        "0cccc00778000ccc",
        "0ccc000077000ccc",
        "0cc00000000000cc",
    ],
    [
        "0000000000000000",
        "00cc000077000cc0",
        "00ccc00778000ccc",
        "00cccc0778000ccc",
        "000cccc77800cccc",
        "0000cccc7880cccc",
        "00000ccc7888cccc",
        "000000cc78888ccc",
        "000000cc78888ccc",
        "00000ccc7888cccc",
        "0000cccc7880cccc",
        "000cccc77800cccc",
        "00cccc0778000ccc",
        "00ccc00778000ccc",
        "00cc000077000cc0",
        "0000000000000000",
    ],
]

# B100F「迷宮の造り主」（16×16、2コマ）。菱形の幾何学体に内部構造。2コマ目は内部が回る
LABYRINTH_MAKER: list[Pixels] = [
    [
        "0000000aa0000000",
        "00000aa77aa00000",
        "0000a7777777a000",
        "000a777aa777a000",
        "00a777a77a777a00",
        "0a777a7777a777a0",
        "a777a777777a777a",
        "a77a77a77a77a77a",
        "a77a77a77a77a77a",
        "a777a777777a777a",
        "0a777a7777a777a0",
        "00a777a77a777a00",
        "000a777aa777a000",
        "0000a7777777a000",
        "00000aa77aa00000",
        "0000000aa0000000",
    ],
    [
        "0000000aa0000000",
        "00000aa77aa00000",
        "0000a7777777a000",
        "000a77a77a77a000",
        "00a77a77777a7a00",
        "0a77a7777777a7a0",
        "a77a7777777777aa",
        "a7a77777777777aa",
        "aa77777777777a7a",
        "aa7777777777a77a",
        "0a7a7777777a77a0",
        "00a7a77777a77a00",
        "000a77a77a77a000",
        "0000a7777777a000",
        "00000aa77aa00000",
        "0000000aa0000000",
    ],
]

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
    # 追加分。体の色は、出現する階の床の色と同じにしない（背景に溶けて見えなくなるため）
    "cave_spider": ("centipede", 1, 7, 0),
    "bog_slime": ("blob", 12, 1, 5),
    "ghoul": ("humanoid", 6, 8, 5),
    "wisp": ("ghost", 10, 7, 9),
    "stone_beetle": ("centipede", 13, 6, 5),
    "bone_knight": ("humanoid", 7, 12, 5),
    "lava_newt": ("beast", 8, 10, 2),
    "void_moth": ("flyer", 14, 7, 2),
}

# 迷宮の行商人（仕様書 12.4）。敵と見間違えないよう、明るい緑の人型にする。
# キー名はゲーム本体の game/world/tiles.py の MERCHANT_SPRITE と合わせること
# （ツールは本体から import しない決まりのため、ここでは同じ文字列を書く）。
MERCHANT_SPRITE = "merchant"
MERCHANT: tuple[str, int, int, int] = ("humanoid", 11, 10, 3)

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
        result[f"floor_{area['id']}"] = [recolor(FLOOR, ground)]
        result[f"corridor_{area['id']}"] = [recolor(CORRIDOR, ground)]
        result[f"wall_{area['id']}"] = [recolor(WALL, wall)]
    return result


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


def boss_sheet() -> dict[str, list[Pixels]]:
    """ボスID → コマのリスト（16×16）。20階ごとのボスは、形で見分けられるようにする。

    色だけを変えると、縮小表示では同じ敵に見えてしまう。輪郭（王冠・岩塊・翼・菱形）を
    別物にして、ひと目で違うボスだと分かるようにする。
    体の色は、ボス階の床の色（1）と床の点の色（2）を避ける（背景に沈むため）。
    """
    return {
        "devourer": BOSS,
        "bone_sovereign": BONE_SOVEREIGN,
        "magma_tyrant": MAGMA_TYRANT,
        "void_seraph": VOID_SERAPH,
        "labyrinth_maker": LABYRINTH_MAKER,
    }


def build_sheet() -> list[dict[str, list[Pixels]]]:
    """名前 → コマのリスト。行ごとに左から詰めて配置する。"""
    monsters = {name: bob(paint(*spec)) for name, spec in MONSTERS.items()}
    monsters[MERCHANT_SPRITE] = bob(paint(*MERCHANT))
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
        area_tiles(),
    ]


def main() -> None:
    size = config.TILE_SIZE
    pyxel.init(64, 64, title="make_placeholder_sprites")
    if config.RESOURCE_PATH.exists():
        pyxel.load(str(config.RESOURCE_PATH))

    image = pyxel.images[0]
    sprites: dict[str, dict[str, int]] = {}
    row = 0
    for entries in build_sheet():
        u = 0
        v = row * size
        for name, frames in entries.items():
            width = len(frames) * size
            if u + width > image.width:
                # 1行に入りきらないので次の行へ送る（敵が増えても破綻しないようにする）
                row += 1
                u, v = 0, row * size
            for i, pixels in enumerate(frames):
                assert len(pixels) == size and all(len(line) == size for line in pixels), name
                image.set(u + i * size, v, pixels)
            sprites[name] = {"u": u, "v": v, "frames": len(frames)}
            u += width
        row += 1

    # ボスだけは 16×16 なので、8×8 の行の下に置く（左から順に並べる）
    boss_v = row * size
    boss_u = 0
    for boss_id, frames in boss_sheet().items():
        boss_size = len(frames[0][0])
        for i, pixels in enumerate(frames):
            assert len(pixels) == boss_size and all(len(line) == boss_size for line in pixels)
            image.set(boss_u + i * boss_size, boss_v, pixels)
        sprites[boss_id] = {
            "u": boss_u,
            "v": boss_v,
            "w": boss_size,
            "h": boss_size,
            "frames": len(frames),
        }
        boss_u += len(frames) * boss_size
    assert boss_u <= image.width, "ボスの行が画像の幅を超えています"

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
