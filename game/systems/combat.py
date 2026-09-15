"""命中・ダメージ計算と攻撃範囲。仕様書 6.5 / 6.8 / 10.2。

pyxel を import しないこと。
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import dataclass_from_dict
from game.world.direction import Direction
from game.world.floor import Floor

# 攻撃範囲の種類
REACH_FRONT = "front"  # 前方1マス
REACH_PIERCE = "pierce"  # 前方 length マス（範囲内の敵すべてに当たる）
REACH_LINE = "line"  # 前方 length マス（最初に当たった敵のみ）
REACH_FAN = "fan"  # 正面とその左右斜め
REACH_AROUND = "around"  # 周囲8マス
REACHES = (REACH_FRONT, REACH_PIERCE, REACH_LINE, REACH_FAN, REACH_AROUND)


@dataclass(frozen=True)
class CombatParams:
    """戦闘のパラメータ。balance.json の "combat" で定義する。"""

    hit_min: int
    hit_max: int
    damage_rand_min: float
    damage_rand_max: float
    def_factor: float
    crit_rate: int
    crit_multiplier: float
    throw_damage: int
    throw_range: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CombatParams:
        return dataclass_from_dict(cls, data, "combat")


@dataclass(frozen=True)
class CombatStats:
    atk: int
    defense: int
    hit: int
    evade: int
    crit_rate: int


@dataclass(frozen=True)
class AttackResult:
    hit: bool
    damage: int = 0
    critical: bool = False


def round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


def hit_chance(attacker: CombatStats, defender: CombatStats, params: CombatParams) -> int:
    return max(params.hit_min, min(params.hit_max, attacker.hit - defender.evade))


def roll_attack(
    attacker: CombatStats,
    defender: CombatStats,
    rng: random.Random,
    params: CombatParams,
    *,
    multiplier: float = 1.0,
    halve: bool = False,
) -> AttackResult:
    """命中判定とダメージを計算する。

    dmg = max(1, round(ATK × rand(0.9, 1.1) − DEF × 0.5))、クリティカルで ×1.5、
    スキルの倍率を掛け、耐性（halve）があれば半減する。
    """
    if rng.randrange(100) >= hit_chance(attacker, defender, params):
        return AttackResult(hit=False)
    spread = rng.uniform(params.damage_rand_min, params.damage_rand_max)
    damage = max(1, round_half_up(attacker.atk * spread - defender.defense * params.def_factor))
    critical = rng.randrange(100) < attacker.crit_rate
    if critical:
        damage = round_half_up(damage * params.crit_multiplier)
    damage = max(1, round_half_up(damage * multiplier))
    if halve:
        damage = max(1, damage // 2)
    return AttackResult(hit=True, damage=damage, critical=critical)


def reach_cells(
    floor: Floor, x: int, y: int, facing: Direction, reach: str, length: int = 1
) -> list[tuple[int, int]]:
    """攻撃が届くマスを近い順に返す。壁と角（角抜け禁止）で遮られたマスは含めない。"""
    if reach == REACH_FRONT:
        return _line(floor, x, y, facing, 1)
    if reach in (REACH_PIERCE, REACH_LINE):
        return _line(floor, x, y, facing, length)
    if reach == REACH_FAN:
        # 斜め向きでも、正面の方向を基準に左右へ45度ずつ広げる
        directions: tuple[Direction, ...] = (facing, facing.rotated(-1), facing.rotated(1))
    elif reach == REACH_AROUND:
        directions = tuple(Direction)
    else:
        raise ValueError(f"不明な攻撃範囲です: {reach}")
    return [(x + d.dx, y + d.dy) for d in directions if floor.can_move(x, y, d)]


def _line(floor: Floor, x: int, y: int, direction: Direction, length: int) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    cx, cy = x, y
    for _ in range(length):
        if not floor.can_move(cx, cy, direction):
            break
        cx, cy = cx + direction.dx, cy + direction.dy
        cells.append((cx, cy))
    return cells
