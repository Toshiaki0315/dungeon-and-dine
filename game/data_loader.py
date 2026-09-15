"""data/ 配下の JSON を読み込み、必須キーを検証する。仕様書 2.7。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from game import config

# ファイル名 → トップレベルに必須のキー。フェーズが進んだら要素単位の検証を追加する。
REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "enemies.json": ("version", "enemies"),
    "weapons.json": ("version", "weapons"),
    "armors.json": ("version", "armors"),
    "items.json": ("version", "items"),
    "ingredients.json": ("version", "ingredients"),
    "recipes.json": ("version", "recipes"),
    "traps.json": ("version", "traps"),
    "status_effects.json": ("version", "status_effects"),
    "skills.json": ("version", "skills"),
    "sprites.json": ("version", "sprites"),
    "palettes.json": ("version", "palettes"),
    "floors.json": ("version", "areas", "floors"),
    "balance.json": ("version",),
}


class DataValidationError(Exception):
    """データファイルの形式が不正なときに送出する。"""


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise DataValidationError(f"{path.name}: トップレベルはオブジェクトである必要があります")
    return data


def load_all(data_dir: Path = config.DATA_DIR) -> dict[str, dict[str, Any]]:
    """全データファイルを読み込み、ファイル名（拡張子なし）をキーにして返す。"""
    result: dict[str, dict[str, Any]] = {}
    for filename, required in REQUIRED_KEYS.items():
        path = data_dir / filename
        if not path.exists():
            raise DataValidationError(f"データファイルがありません: {path}")
        data = load_json(path)
        missing = [key for key in required if key not in data]
        if missing:
            raise DataValidationError(f"{filename}: 必須キーがありません: {', '.join(missing)}")
        result[path.stem] = data
    return result
