"""エントリポイント: 起動引数を解析して App を起動する。"""

from __future__ import annotations

import argparse

from game import config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dungeon & Dine: 飢餓のトレジャーハンター")
    parser.add_argument("--seed", type=int, default=None, help="ランシードを固定する（再現用）")
    parser.add_argument(
        "--scale", type=int, default=config.DISPLAY_SCALE, help="表示倍率（既定: 4）"
    )
    parser.add_argument(
        "--debug", action="store_true", help="開発ビルド扱い（F1 デバッグ表示を有効化）"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # pyxel はここで初めて import する（ロジック層のテストに影響させないため）
    from game.app import App

    App(seed=args.seed, display_scale=args.scale, debug=args.debug).run()


if __name__ == "__main__":
    main()
