"""モンスター。仕様書 8.2。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import DataValidationError
from game.entities.entity import Entity
from game.entities.item import CHEST_CLOSED_SPRITE
from game.systems.combat import CombatStats

AI_CHASE = "chase"
AI_WANDER = "wander"
AI_ERRATIC = "erratic"
AI_RANGED = "ranged"
AI_AMBUSH = "ambush"
AI_FLEE = "flee"
AI_TYPES = (AI_CHASE, AI_WANDER, AI_ERRATIC, AI_RANGED, AI_AMBUSH, AI_FLEE)

MODE_IDLE = "idle"  # その場で待つ
MODE_WANDER = "wander"  # ランダムに徘徊する
MODE_CHASE = "chase"  # プレイヤー（または最後に見た位置）へ向かう

ABILITY_ON_HIT_STATUS = "on_hit_status"
ABILITY_BREATH = "breath"

CHEST_SPRITE = CHEST_CLOSED_SPRITE  # ミミックの擬態中の見た目


@dataclass(frozen=True)
class Ability:
    type: str
    status: str | None = None
    chance: int = 100
    range: int = 0
    element: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Ability:
        return cls(
            type=str(data["type"]),
            status=data.get("status"),
            chance=int(data.get("chance", 100)),
            range=int(data.get("range", 0)),
            element=data.get("element"),
        )


@dataclass(frozen=True)
class MonsterDef:
    id: str
    name: str
    first_floor: int
    last_floor: int
    hp: int
    atk: int
    defense: int
    exp: int
    speed: int
    ai: str
    hit: int
    evade: int
    sprite: str
    abilities: tuple[Ability, ...] = ()
    drop: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MonsterDef:
        required = (
            "id", "name", "floors", "hp", "atk", "defense", "exp",
            "speed", "ai", "hit", "evade", "sprite",
        )  # fmt: skip
        missing = [key for key in required if key not in data]
        if missing:
            raise DataValidationError(
                f"enemies.json: {data.get('id', '?')}: 必須キーがありません: {', '.join(missing)}"
            )
        if data["ai"] not in AI_TYPES:
            raise DataValidationError(f"enemies.json: {data['id']}: 不明な AI です: {data['ai']}")
        first, last = data["floors"]
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            first_floor=int(first),
            last_floor=int(last),
            hp=int(data["hp"]),
            atk=int(data["atk"]),
            defense=int(data["defense"]),
            exp=int(data["exp"]),
            speed=int(data["speed"]),
            ai=str(data["ai"]),
            hit=int(data["hit"]),
            evade=int(data["evade"]),
            sprite=str(data["sprite"]),
            abilities=tuple(Ability.from_dict(a) for a in data.get("abilities", ())),
            drop=data.get("drop"),
        )


@dataclass(eq=False, kw_only=True)
class Monster(Entity):
    definition: MonsterDef
    uid: int  # 生成順（行動順に使う）
    hp: int
    mode: str
    target: tuple[int, int] | None = None  # 追いかけている位置
    disguised: bool = False

    @classmethod
    def spawn(cls, definition: MonsterDef, x: int, y: int, uid: int) -> Monster:
        mode = MODE_WANDER if definition.ai in (AI_WANDER, AI_ERRATIC) else MODE_IDLE
        return cls(
            x=x,
            y=y,
            speed=definition.speed,
            definition=definition,
            uid=uid,
            hp=definition.hp,
            mode=mode,
            disguised=definition.ai == AI_AMBUSH,
        )

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def max_hp(self) -> int:
        return self.definition.hp

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    @property
    def sprite_name(self) -> str:
        return CHEST_SPRITE if self.disguised else self.definition.sprite

    def combat_stats(self, crit_rate: int) -> CombatStats:
        d = self.definition
        return CombatStats(
            atk=d.atk, defense=d.defense, hit=d.hit, evade=d.evade, crit_rate=crit_rate
        )

    def ability(self, ability_type: str) -> Ability | None:
        return next((a for a in self.definition.abilities if a.type == ability_type), None)
