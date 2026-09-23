"""ドット絵の一覧画像を作るスクリプト（デザイン確認用）。

    .venv/bin/python tools/make_sprite_catalog.py

`data/sprites.json` と `assets/resources.pyxres` を読んで、次の3枚を書き出す。

- `01_sprites.png` — 地形・敵・アイテム・罠など（既定で4倍）
- `02_heroes.png` — 主人公の見た目（向きごとの2コマ。既定で5倍）
- `03_bosses.png` — ボス（32×32、2コマ。既定で5倍）

書き出し先は既定で `sprite_catalog/`（.gitignore 済み。画像はリポジトリに含めない）。
ゲーム本体からは import しないこと。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pyxel  # noqa: E402

from game import config  # noqa: E402
from game.entities.player import APPEARANCE_IDS, PLAYER_SPRITE_BASE  # noqa: E402

BOSS_NAMES: tuple[str, ...] = (
    "devourer",
    "bone_sovereign",
    "magma_tyrant",
    "void_seraph",
    "labyrinth_maker",
)
LABEL_COLOR = 7
HEADER_COLOR = 10
LABEL_MAX = 17  # 組み込みフォント（4px 幅）で1マスに収まる文字数
HEADER_H = 8
PADDING = 4


def load_defs() -> dict[str, dict[str, int]]:
    data = json.loads((config.DATA_DIR / "sprites.json").read_text(encoding="utf-8"))
    return data["sprites"]


def size_of(entry: dict[str, int]) -> tuple[int, int]:
    return entry.get("w", config.SPRITE_SIZE), entry.get("h", config.SPRITE_SIZE)


def draw_sprite(
    dst: pyxel.Image,
    entry: dict[str, int],
    x: int,
    y: int,
    scale: int,
    frame: int,
    label: str | None,
) -> None:
    """素材を1ドット＝scale ドットの正方形で拡大して描き、下に名前を書く。"""
    w, h = size_of(entry)
    src = pyxel.images[entry.get("bank", 0)]
    for j in range(h):
        for i in range(w):
            color = src.pget(entry["u"] + frame * w + i, entry["v"] + j)
            if color:  # 0（透過色）は描かない
                dst.rect(x + i * scale, y + j * scale, scale, scale, color)
    if label is not None:
        dst.text(x, y + h * scale + 3, label[:LABEL_MAX], LABEL_COLOR)


def make_sheet(
    path: Path,
    defs: dict[str, dict[str, int]],
    names: list[str],
    *,
    cols: int,
    scale: int,
    frames: int,
    header: str,
) -> None:
    if not names:
        return
    cell_w = max(size_of(defs[n])[0] for n in names) * scale * frames + 6 * frames + PADDING
    cell_h = max(size_of(defs[n])[1] for n in names) * scale + 14
    rows = (len(names) + cols - 1) // cols
    image = pyxel.Image(cols * cell_w, rows * cell_h + HEADER_H)
    image.cls(0)
    image.text(PADDING, 3, header, HEADER_COLOR)
    for index, name in enumerate(names):
        entry = defs[name]
        w = size_of(entry)[0]
        x = (index % cols) * cell_w + PADDING
        y = (index // cols) * cell_h + PADDING + HEADER_H
        for frame in range(min(frames, entry.get("frames", 1))):
            draw_sprite(
                image,
                entry,
                x + frame * (w * scale + 6),
                y,
                scale,
                frame,
                name if frame == 0 else None,
            )
    image.save(str(path), 1)
    print(f"{path} を書き出しました（{len(names)} 件）")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ドット絵の一覧画像を作る")
    parser.add_argument(
        "--out", type=Path, default=ROOT_DIR / "sprite_catalog", help="書き出し先のフォルダ"
    )
    parser.add_argument("--scale", type=int, default=4, help="拡大率（既定: 4）")
    args = parser.parse_args(argv)

    pyxel.init(64, 64, title="make_sprite_catalog")
    pyxel.load(str(config.RESOURCE_PATH))
    defs = load_defs()
    args.out.mkdir(parents=True, exist_ok=True)

    hero_prefix = f"{PLAYER_SPRITE_BASE}_"
    heroes = [n for n in defs if n.startswith(hero_prefix)]
    bosses = [n for n in defs if n in BOSS_NAMES]
    others = [n for n in defs if n not in heroes and n not in bosses]
    hero_scale = args.scale + 1

    make_sheet(
        args.out / "01_sprites",
        defs,
        others,
        cols=10,
        scale=args.scale,
        frames=1,
        header=f"Dungeon & Dine sprites ({args.scale}x)",
    )
    make_sheet(
        args.out / "02_heroes",
        defs,
        heroes,
        cols=4,
        scale=hero_scale,
        frames=2,
        header=f"heroes: {len(APPEARANCE_IDS)} appearances x 4 facings x 2 frames ({hero_scale}x)",
    )
    make_sheet(
        args.out / "03_bosses",
        defs,
        bosses,
        cols=2,
        scale=hero_scale,
        frames=2,
        header=f"bosses: 32x32, 2 frames ({hero_scale}x)",
    )
    pyxel.quit()


if __name__ == "__main__":
    main()
