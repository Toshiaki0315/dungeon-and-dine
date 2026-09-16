"""状態異常・バフ。仕様書 7章。

pyxel を import しないこと。
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import DataValidationError
from game.systems.turn import NORMAL_SPEED

AILMENT = "ailment"
BUFF = "buff"
UNTIL_FLOOR_CHANGE = -1  # 階を移るまで続く


@dataclass(frozen=True)
class StatusDef:
    id: str
    name: str
    kind: str  # "ailment"（異常）または "buff"（バフ）
    duration: int | None  # None は階を移るまで
    value: int = 0  # 効果量（ATK +3、速度 200 など）

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StatusDef:
        missing = [key for key in ("id", "name", "kind", "duration") if key not in data]
        if missing:
            raise DataValidationError(
                f"status_effects.json: {data.get('id', '?')}: 必須キーがありません: "
                f"{', '.join(missing)}"
            )
        if data["kind"] not in (AILMENT, BUFF):
            raise DataValidationError(f"status_effects.json: {data['id']}: kind が不正です")
        duration = data["duration"]
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            kind=str(data["kind"]),
            duration=None if duration is None else int(duration),
            value=int(data.get("value", 0)),
        )


class StatusEffects:
    """エンティティにかかっている状態異常・バフと、その残りターン。"""

    def __init__(self) -> None:
        self._remaining: dict[str, int] = {}
        self._stacks: dict[str, int] = {}

    def __contains__(self, status_id: object) -> bool:
        return status_id in self._remaining

    def active_ids(self) -> list[str]:
        return list(self._remaining)

    def remaining(self, status_id: str) -> int | None:
        return self._remaining.get(status_id)

    def stacks(self, status_id: str) -> int:
        return self._stacks.get(status_id, 0)

    def add(self, definition: StatusDef, duration: int | None = None) -> None:
        turns = definition.duration if duration is None else duration
        new = UNTIL_FLOOR_CHANGE if turns is None else turns
        current = self._remaining.get(definition.id)
        if current is not None and UNTIL_FLOOR_CHANGE not in (current, new):
            new = max(current, new)  # 同じ効果が重なったら、持続ターンは長いほうで上書きする
        self._remaining[definition.id] = new
        self._stacks[definition.id] = self._stacks.get(definition.id, 0) + 1

    def remove(self, status_id: str) -> bool:
        self._stacks.pop(status_id, None)
        return self._remaining.pop(status_id, None) is not None

    def tick(self) -> list[str]:
        """1ターン経過させ、切れた効果の ID を返す。"""
        expired: list[str] = []
        for status_id, turns in list(self._remaining.items()):
            if turns == UNTIL_FLOOR_CHANGE:
                continue
            if turns <= 1:
                self.remove(status_id)
                expired.append(status_id)
            else:
                self._remaining[status_id] = turns - 1
        return expired

    def snapshot(self) -> dict[str, list[int]]:
        """保存用に、状態異常IDごとの [残りターン, 重ねがけ数] を返す（仕様書 13章）。"""
        return {
            status_id: [turns, self._stacks.get(status_id, 1)]
            for status_id, turns in self._remaining.items()
        }

    def restore(self, snapshot: Mapping[str, list[int]]) -> None:
        self._remaining = {status_id: int(v[0]) for status_id, v in snapshot.items()}
        self._stacks = {status_id: int(v[1]) for status_id, v in snapshot.items()}

    def clear_until_floor_change(self) -> dict[str, int]:
        """「階を移るまで」の効果を解除し、ID と重ねがけ数を返す。"""
        removed = {
            status_id: self._stacks.get(status_id, 1)
            for status_id, turns in self._remaining.items()
            if turns == UNTIL_FLOOR_CHANGE
        }
        for status_id in removed:
            self.remove(status_id)
        return removed


def try_inflict(
    statuses: StatusEffects,
    definition: StatusDef,
    rng: random.Random,
    chance: int = 100,
    duration: int | None = None,
    *,
    resist_all: bool = False,
) -> bool:
    """効果を付与する。異常は耐性で防いだり、かかる確率が半減したりする。"""
    if definition.kind == AILMENT:
        if definition.id == "poison" and "poison_resist" in statuses:
            return False
        if "status_resist" in statuses or resist_all:
            chance //= 2
    if chance < 100 and rng.randrange(100) >= chance:
        return False
    statuses.add(definition, duration)
    return True


def speed_for(statuses: StatusEffects, catalog: Mapping[str, StatusDef]) -> int:
    """鈍足・倍速を反映した速度。両方かかっている場合は打ち消し合う。"""
    slow = "slow" in statuses
    haste = "haste" in statuses
    if slow == haste:
        return NORMAL_SPEED
    return catalog["haste"].value if haste else catalog["slow"].value
