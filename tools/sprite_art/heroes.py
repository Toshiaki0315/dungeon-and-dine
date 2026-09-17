"""主人公の見た目5種（16×16、向きごとに待機・歩行の2コマ）。

戦士・格闘家・魔法使い・僧侶・商人。見た目だけの違いで、能力は変わらない。
キーはゲーム本体の game/entities/player.py の APPEARANCES と合わせること
（ツールは本体から import しない決まりのため、ここでは同じ文字列を書く）。
左向きは右向きを左右反転して作る。
"""

from sprite_art import Pixels, patch


def _stride_front(leg: str, foot: str) -> dict[int, str]:
    """ズボンの脚で、正面・背面を向いて歩く2コマ目（足を前後に開く）。"""
    return {
        13: f"000{leg * 3}0000{leg * 3}000",
        14: f"00{leg * 3}000000{leg * 3}00",
        15: f"0{foot * 4}000000{foot * 4}0",
    }


def _stride_side(leg: str, foot: str) -> dict[int, str]:
    """ズボンの脚で、横を向いて歩く2コマ目。"""
    return {
        13: f"0000{leg * 2}0000{leg * 2}0000",
        14: f"000{leg * 2}000000{leg * 2}000",
        15: f"00{foot * 3}000000{foot * 4}0",
    }


# --- 戦士: 赤い房飾りの兜、肩当てと胸当て、赤い腰布 ---
WARRIOR_DOWN: Pixels = [
    "0000000880000000",
    "00000dd88dd00000",
    "0000d6dddddd0000",
    "000d6dddddddd000",
    "000ddffffffdd000",
    "000df1ffff1fd000",
    "0000dffffffd0000",
    "00000dffffd00000",
    "00dd66dddd66dd00",
    "0dddd6dddd6dddd0",
    "0dd8d6dddd6d8dd0",
    "0f844444444448f0",
    "0000888888880000",
    "0000ddd00ddd0000",
    "0000ddd00ddd0000",
    "0004444004444000",
]
WARRIOR_UP: Pixels = [
    "0000000880000000",
    "00000dd88dd00000",
    "0000dddddddd0000",
    "000dddddddddd000",
    "000dddddddddd000",
    "000dddddddddd000",
    "0000dddddddd0000",
    "00000dddddd00000",
    "00dd66dddd66dd00",
    "0dddd888888dddd0",
    "0dd8888888888dd0",
    "0f888888888888f0",
    "0000888888880000",
    "0000ddd00ddd0000",
    "0000ddd00ddd0000",
    "0004444004444000",
]
WARRIOR_RIGHT: Pixels = [
    "0000088000000000",
    "0000ddd88dd00000",
    "0000dddddd6dd000",
    "000dddddddd6dd00",
    "000ddddddffff000",
    "000dddddfff1f000",
    "0000ddddfffff000",
    "00000dddfffd0000",
    "0000dd66dddd0000",
    "0000d66ddddd0000",
    "00008ddddd6f0000",
    "0000844444448000",
    "0000088888888000",
    "00000dd00dd00000",
    "00000dd00dd00000",
    "0000044400444400",
]

# --- 格闘家: 逆立った橙の髪、赤い鉢巻、袖のない白い道着、黒帯、素足 ---
FIGHTER_DOWN: Pixels = [
    "0000900990090000",
    "0000999999990000",
    "0009999999999000",
    "0008888888888000",
    "0009ffffffff9000",
    "0009f1ffff1f9000",
    "0000ffffffff0000",
    "00000ffffff00000",
    "00ff77777777ff00",
    "0ff0777ff7770ff0",
    "0ff0777777770ff0",
    "0880111111110880",
    "0000777007770000",
    "0000777007770000",
    "0000777007770000",
    "000ffff00ffff000",
]
FIGHTER_UP: Pixels = [
    "0000900990090000",
    "0000999999990000",
    "0009999999999000",
    "0008888888888000",
    "0009999999999880",
    "0009999999999080",
    "0000999999990000",
    "00000ffffff00000",
    "00ff77777777ff00",
    "0ff0777777770ff0",
    "0ff0777777770ff0",
    "0880111111110880",
    "0000777007770000",
    "0000777007770000",
    "0000777007770000",
    "000ffff00ffff000",
]
FIGHTER_RIGHT: Pixels = [
    "0009009009000000",
    "0009999999900000",
    "0009999999999000",
    "0888888888888000",
    "8009999ffffff000",
    "0009999fff1ff000",
    "00009999fffff000",
    "000009ffffff0000",
    "00000f77777f0000",
    "0000ff77777ff000",
    "00000777777f8000",
    "0000011111110000",
    "0000077777770000",
    "0000077007700000",
    "0000077007700000",
    "00000fff00ffff00",
]

# --- 魔法使い: 青いとんがり帽子と長衣、金の縁取り、宝玉の杖 ---
MAGE_DOWN: Pixels = [
    "000000000c000000",
    "00000000cc000000",
    "0000000ccc000a00",
    "000000cc6cc0aaa0",
    "00000cccccc00a00",
    "000aaaaaaaaaa400",
    "00004ffffff40400",
    "00004f1ff1f40400",
    "000000ffff000400",
    "0000cccccccc0400",
    "000ccccaaccccf00",
    "000ccccaacccc400",
    "000ccccaacccc400",
    "000ccccaacccc400",
    "000aaaaaaaaaa400",
    "0000440000440400",
]
MAGE_UP: Pixels = [
    "000000000c000000",
    "00000000cc000000",
    "0000000ccc000a00",
    "000000cc6cc0aaa0",
    "00000cccccc00a00",
    "000aaaaaaaaaa400",
    "0000444444440400",
    "0000444444440400",
    "00000cccccc00400",
    "0000cccccccc0400",
    "000ccccccccccf00",
    "000cccccccccc400",
    "000cccccccccc400",
    "000cccccccccc400",
    "000aaaaaaaaaa400",
    "0000440000440400",
]
MAGE_RIGHT: Pixels = [
    "000000c000000000",
    "0000000cc0000000",
    "0000000ccc000a00",
    "000000cc6cc0aaa0",
    "00000cccccc00a00",
    "000aaaaaaaaaa400",
    "00004444fff00400",
    "0000444ff1f00400",
    "0000004fff000400",
    "00000cccccc00400",
    "0000cccccccccf00",
    "0000cccaccccc400",
    "0000cccaccccc400",
    "0000cccaccccc400",
    "0000aaaaaaaaa400",
    "0000044000440400",
]
_MAGE_STRIDE = {15: "0004400000440400"}

# --- 僧侶: 青い縁の白い頭巾と法衣、金の十字、聖典 ---
PRIEST_DOWN: Pixels = [
    "0000077777700000",
    "0000777777770000",
    "0007cccccccc7000",
    "0007ffffffff7000",
    "0007f1ffff1f7000",
    "0007ffffffff7000",
    "00077ffffff77000",
    "0077777777777700",
    "0777777aa7777770",
    "0f7777aaaa7777f0",
    "0077777aa7777700",
    "00c7777aa7777c00",
    "00c7777777777c00",
    "00c7777777777c00",
    "00cccccccccccc00",
    "0000dd0000dd0000",
]
PRIEST_UP: Pixels = [
    "0000077777700000",
    "0000777777770000",
    "0007777777777000",
    "0007777777777000",
    "0007777777777000",
    "0007777777777000",
    "0007777777777000",
    "0077777777777700",
    "0777777777777770",
    "0777777cc7777770",
    "0077777cc7777700",
    "00c7777777777c00",
    "00c7777777777c00",
    "00c7777777777c00",
    "00cccccccccccc00",
    "0000dd0000dd0000",
]
PRIEST_RIGHT: Pixels = [
    "0000777777000000",
    "0007777777700000",
    "00777777cccc0000",
    "0077777fffff0000",
    "0077777fff1f0000",
    "0077777fffff0000",
    "00777777fff00000",
    "0077777777770000",
    "0007777777770000",
    "000777777fcc0000",
    "000777777fcc0000",
    "000c777777770000",
    "000c777777770000",
    "000c7777777c0000",
    "000ccccccccc0000",
    "00000dd00dd00000",
]
_PRIEST_STRIDE_FRONT = {15: "000dd000000dd000"}
_PRIEST_STRIDE_SIDE = {15: "0000dd0000dd0000"}

# --- 商人: つば広の帽子、口ひげ、白いシャツに橙のベスト、金の財布、大きな背負い袋 ---
MERCHANT_DOWN: Pixels = [
    "0000004444000000",
    "0000044444400000",
    "00000aaaaaa00000",
    "0044444444444400",
    "00004ffffff40000",
    "00004f1ff1f40000",
    "00000f4444f00000",
    "000000ffff000000",
    "0044977777794400",
    "0444977777794440",
    "0444997777994440",
    "0f44944aa44944f0",
    "0000dddddddd0000",
    "0000ddd00ddd0000",
    "0000ddd00ddd0000",
    "0004444004444000",
]
MERCHANT_UP: Pixels = [
    "0000004444000000",
    "0000044444400000",
    "00000aaaaaa00000",
    "0044444444444400",
    "0000444444440000",
    "0000444444440000",
    "0000044444400000",
    "0004444444444000",
    "0044499999944400",
    "0444494aa4944440",
    "0444444444444440",
    "0f444444444444f0",
    "0000dddddddd0000",
    "0000ddd00ddd0000",
    "0000ddd00ddd0000",
    "0004444004444000",
]
MERCHANT_RIGHT: Pixels = [
    "0000044440000000",
    "0000444444000000",
    "0000aaaaaa000000",
    "0044444444444440",
    "00004444ffff0000",
    "00004444ff1f0000",
    "00004444fff44000",
    "0444400ffff00000",
    "4444497777900000",
    "4a444977777f0000",
    "4444499777900000",
    "044440944aa00000",
    "00000dddddd00000",
    "00000dd00dd00000",
    "00000dd00dd00000",
    "0000044400444400",
]


def _walk(frame: Pixels, stride: dict[int, str]) -> list[Pixels]:
    return [frame, patch(frame, stride)]


def _mirror(frames: list[Pixels]) -> list[Pixels]:
    return [[row[::-1] for row in frame] for frame in frames]


def _hero(
    down: Pixels, up: Pixels, right: Pixels, front: dict[int, str], side: dict[int, str]
) -> dict[str, list[Pixels]]:
    """向き（down/up/left/right）→ 2コマ。"""
    right_frames = _walk(right, side)
    return {
        "down": _walk(down, front),
        "up": _walk(up, front),
        "left": _mirror(right_frames),
        "right": right_frames,
    }


HEROES: dict[str, dict[str, list[Pixels]]] = {
    "warrior": _hero(
        WARRIOR_DOWN, WARRIOR_UP, WARRIOR_RIGHT, _stride_front("d", "4"), _stride_side("d", "4")
    ),
    "fighter": _hero(
        FIGHTER_DOWN, FIGHTER_UP, FIGHTER_RIGHT, _stride_front("7", "f"), _stride_side("7", "f")
    ),
    "mage": _hero(MAGE_DOWN, MAGE_UP, MAGE_RIGHT, _MAGE_STRIDE, _MAGE_STRIDE),
    "priest": _hero(
        PRIEST_DOWN, PRIEST_UP, PRIEST_RIGHT, _PRIEST_STRIDE_FRONT, _PRIEST_STRIDE_SIDE
    ),
    "merchant": _hero(
        MERCHANT_DOWN,
        MERCHANT_UP,
        MERCHANT_RIGHT,
        _stride_front("d", "4"),
        _stride_side("d", "4"),
    ),
}
