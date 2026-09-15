"""スキル。仕様書 6.8。

スキルを使ったときの処理は systems/game_state.py にある。
pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import DataValidationError

SKILL_ATTACK = "attack"
SKILL_STEALTH = "stealth"
SKILL_APPRAISE = "appraise"  # フェーズ4
SKILL_CAMPFIRE = "campfire"  # フェーズ5
SKILL_TYPES = (SKILL_ATTACK, SKILL_STEALTH, SKILL_APPRAISE, SKILL_CAMPFIRE)


@dataclass(frozen=True)
class SkillDef:
    id: str
    name: str
    level: int
    mp: int
    type: str
    description: str
    area: str | None = None  # 攻撃スキルの範囲（combat.REACH_*）
    multiplier: float = 1.0
    duration: int = 0
    self_damage_ratio: float = 0.0
    guaranteed_drop: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SkillDef:
        required = ("id", "name", "level", "mp", "type", "description")
        missing = [key for key in required if key not in data]
        if missing:
            raise DataValidationError(
                f"skills.json: {data.get('id', '?')}: 必須キーがありません: {', '.join(missing)}"
            )
        if data["type"] not in SKILL_TYPES:
            raise DataValidationError(f"skills.json: {data['id']}: 不明な種類です")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            level=int(data["level"]),
            mp=int(data["mp"]),
            type=str(data["type"]),
            description=str(data["description"]),
            area=data.get("area"),
            multiplier=float(data.get("multiplier", 1.0)),
            duration=int(data.get("duration", 0)),
            self_damage_ratio=float(data.get("self_damage_ratio", 0.0)),
            guaranteed_drop=bool(data.get("guaranteed_drop", False)),
        )


def skills_up_to_level(level: int, skills: Mapping[str, SkillDef]) -> list[str]:
    """そのレベルまでに習得するスキルの ID（習得レベル順）。"""
    learned = [s for s in skills.values() if s.level <= level]
    return [s.id for s in sorted(learned, key=lambda s: s.level)]
