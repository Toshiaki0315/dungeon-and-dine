"""罠の定義と発見。仕様書 12.1。

罠を踏んだときの効果は systems/game_state.py で処理する。
pyxel を import しないこと。
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import DataValidationError, dataclass_from_dict
from game.world.direction import Direction
from game.world.floor import Floor

TRAP_PIT = "pit"
TRAP_DAMAGE_STATUS = "damage_status"
TRAP_STATUS = "status"
TRAP_WARP = "warp"
TRAP_SATIETY = "satiety"
TRAP_RUST = "rust"
TRAP_ALARM = "alarm"
TRAP_EFFECTS = (
    TRAP_PIT, TRAP_DAMAGE_STATUS, TRAP_STATUS, TRAP_WARP, TRAP_SATIETY, TRAP_RUST, TRAP_ALARM,
)  # fmt: skip


@dataclass(frozen=True)
class TrapParams:
    """罠のパラメータ。balance.json の "traps" で定義する。"""

    search_chance: int  # 足踏み時に周囲の罠を発見する確率（%）

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrapParams:
        return dataclass_from_dict(cls, data, "traps")


@dataclass(frozen=True)
class TrapDef:
    id: str
    name: str
    sprite: str
    effect: str
    damage: int = 0
    status: str | None = None
    value: int = 0
    spawn_weight: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrapDef:
        missing = [key for key in ("id", "name", "sprite", "effect") if key not in data]
        if missing:
            raise DataValidationError(
                f"traps.json: {data.get('id', '?')}: 必須キーがありません: {', '.join(missing)}"
            )
        if data["effect"] not in TRAP_EFFECTS:
            raise DataValidationError(f"traps.json: {data['id']}: 不明な効果です")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            sprite=str(data["sprite"]),
            effect=str(data["effect"]),
            damage=int(data.get("damage", 0)),
            status=data.get("status"),
            value=int(data.get("value", 0)),
            spawn_weight=int(data.get("spawn_weight", 0)),
        )


@dataclass(eq=False)
class Trap:
    definition: TrapDef
    x: int
    y: int
    discovered: bool = False

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def name(self) -> str:
        return self.definition.name


def search_around(floor: Floor, x: int, y: int, rng: random.Random, chance: int) -> list[Trap]:
    """周囲8マスの未発見の罠を、それぞれ chance % で発見する。"""
    found: list[Trap] = []
    for direction in Direction:
        trap = floor.trap_at(x + direction.dx, y + direction.dy)
        if trap is not None and not trap.discovered and rng.randrange(100) < chance:
            trap.discovered = True
            found.append(trap)
    return found
