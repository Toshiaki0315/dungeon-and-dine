"""data/ 配下の JSON を読み込み、必須キーを検証する。仕様書 2.7。"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar, get_type_hints

from game import config

# ファイル名 → トップレベルに必須のキー。フェーズが進んだら要素単位の検証を追加する。
REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "enemies.json": ("version", "enemies"),
    "weapons.json": ("version", "weapons", "unarmed"),
    "armors.json": ("version", "armors"),
    "items.json": ("version", "items"),
    "ingredients.json": ("version", "ingredients"),
    "recipes.json": ("version", "recipes"),
    "traps.json": ("version", "traps"),
    "status_effects.json": ("version", "status_effects"),
    "skills.json": ("version", "skills"),
    "sprites.json": ("version", "sprites"),
    "palettes.json": ("version", "palettes"),
    "sounds.json": ("version", "se", "bgm"),
    "floors.json": ("version", "areas", "floors"),
    "balance.json": (
        "version",
        "mapgen",
        "player",
        "survival",
        "progression",
        "combat",
        "spawn",
        "ai",
        "traps",
        "equipment",
        "cooking",
        "base_camp",
        "fov",
        "inventory",
        "input",
    ),
}


class DataValidationError(ValueError):
    """データファイルの形式が不正なときに送出する。"""


@dataclass(frozen=True)
class SpriteDef:
    """イメージバンク上の素材の位置。アニメーションのコマは右方向に並べる。"""

    u: int
    v: int
    w: int = config.TILE_SIZE
    h: int = config.TILE_SIZE
    frames: int = 1
    bank: int = 0


T = TypeVar("T")


def dataclass_from_dict(cls: type[T], data: Mapping[str, Any], section: str) -> T:
    """dataclass のフィールド名と型に従って、JSON の辞書から値を読み込む。"""
    hints = get_type_hints(cls)
    names = [f.name for f in fields(cls)]  # type: ignore[arg-type]
    missing = [name for name in names if name not in data]
    if missing:
        raise DataValidationError(f"{section}: 必須キーがありません: {', '.join(missing)}")
    return cls(**{name: hints[name](data[name]) for name in names})


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


def parse_sprites(data: Mapping[str, Any]) -> dict[str, SpriteDef]:
    """sprites.json の内容を SpriteDef の辞書に変換する。"""
    result: dict[str, SpriteDef] = {}
    for name, entry in data["sprites"].items():
        missing = [key for key in ("u", "v") if key not in entry]
        if missing:
            raise DataValidationError(
                f"sprites.json: {name}: 必須キーがありません: {', '.join(missing)}"
            )
        sprite = SpriteDef(
            u=int(entry["u"]),
            v=int(entry["v"]),
            w=int(entry.get("w", config.TILE_SIZE)),
            h=int(entry.get("h", config.TILE_SIZE)),
            frames=int(entry.get("frames", 1)),
            bank=int(entry.get("bank", data.get("image_bank", 0))),
        )
        if sprite.frames < 1:
            raise DataValidationError(f"sprites.json: {name}: frames は1以上にしてください")
        result[name] = sprite
    return result


def require_sprites(defs: Mapping[str, SpriteDef], names: Iterable[str]) -> None:
    missing = sorted(set(names) - defs.keys())
    if missing:
        raise DataValidationError(f"sprites.json: 素材が定義されていません: {', '.join(missing)}")
