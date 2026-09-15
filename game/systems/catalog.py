"""data/ の定義（敵・アイテム・罠・状態異常・スキル）をまとめて読み込み、相互参照を検証する。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import DataValidationError
from game.entities.item import GOLD_ID, ItemDef, WeaponStats
from game.entities.monster import ABILITY_ON_HIT_STATUS, CHEST_SPRITE, MonsterDef
from game.systems.combat import REACHES
from game.systems.skills import SKILL_ATTACK, SkillDef
from game.systems.status import StatusDef
from game.systems.traps import TrapDef

# コードから ID で参照する状態異常（status_effects.json に必ず定義する）
REQUIRED_STATUSES = (
    "poison", "confusion", "sleep", "slow", "blind", "max_hp_down", "mana_drain",
    "atk_up", "def_up", "haste", "fire_resist", "poison_resist", "status_resist",
    "sight_up", "stealth",
)  # fmt: skip


@dataclass(frozen=True)
class Catalog:
    monsters: Mapping[str, MonsterDef]
    items: Mapping[str, ItemDef]  # 武器も含む
    unarmed: WeaponStats
    traps: Mapping[str, TrapDef]
    statuses: Mapping[str, StatusDef]
    skills: Mapping[str, SkillDef]
    spawn_tables: Mapping[int, Mapping[str, int]]  # 階層 → 敵ID → 出現の重み

    @classmethod
    def from_data(cls, data: Mapping[str, Mapping[str, Any]]) -> Catalog:
        items = _by_id(
            [ItemDef.from_dict(d, "items.json") for d in data["items"]["items"]]
            + [ItemDef.from_dict({**d, "category": "weapon"}, "weapons.json")
               for d in data["weapons"]["weapons"]],
            "items.json / weapons.json",
        )  # fmt: skip
        catalog = cls(
            monsters=_by_id(
                [MonsterDef.from_dict(d) for d in data["enemies"]["enemies"]], "enemies.json"
            ),
            items=items,
            unarmed=WeaponStats.from_dict(data["weapons"]["unarmed"]),
            traps=_by_id([TrapDef.from_dict(d) for d in data["traps"]["traps"]], "traps.json"),
            statuses=_by_id(
                [StatusDef.from_dict(d) for d in data["status_effects"]["status_effects"]],
                "status_effects.json",
            ),
            skills=_by_id([SkillDef.from_dict(d) for d in data["skills"]["skills"]], "skills.json"),
            spawn_tables={
                int(entry["floor"]): {str(k): int(v) for k, v in entry["monsters"].items()}
                for entry in data["floors"]["floors"]
            },
        )  # fmt: skip
        catalog._validate()
        return catalog

    def spawn_table(self, floor_number: int) -> Mapping[str, int]:
        return self.spawn_tables.get(floor_number, {})

    def sprite_names(self) -> set[str]:
        """敵・アイテム・罠の定義が参照する sprites.json のキー。"""
        names = {CHEST_SPRITE}
        names.update(m.sprite for m in self.monsters.values())
        names.update(i.sprite for i in self.items.values())
        names.update(t.sprite for t in self.traps.values())
        return names

    def _validate(self) -> None:
        errors: list[str] = []
        errors += [f"status_effects.json: {s} がありません" for s in REQUIRED_STATUSES
                   if s not in self.statuses]  # fmt: skip
        if GOLD_ID not in self.items:
            errors.append("items.json: gold がありません")
        for monster in self.monsters.values():
            for ability in monster.abilities:
                if ability.type == ABILITY_ON_HIT_STATUS and ability.status not in self.statuses:
                    errors.append(
                        f"enemies.json: {monster.id}: 状態異常 {ability.status} がありません"
                    )
        for item in self.items.values():
            if item.weapon is not None and item.weapon.reach not in REACHES:
                errors.append(f"weapons.json: {item.id}: 攻撃範囲 {item.weapon.reach} が不正です")
            for effect in item.effects:
                errors += [f"items.json: {item.id}: 状態異常 {s} がありません"
                           for s in effect.statuses if s not in self.statuses]  # fmt: skip
        for trap in self.traps.values():
            if trap.status is not None and trap.status not in self.statuses:
                errors.append(f"traps.json: {trap.id}: 状態異常 {trap.status} がありません")
        for skill in self.skills.values():
            if skill.type == SKILL_ATTACK and skill.area not in REACHES:
                errors.append(f"skills.json: {skill.id}: 攻撃範囲 {skill.area} が不正です")
        for floor_number, table in self.spawn_tables.items():
            for monster_id in table:
                monster = self.monsters.get(monster_id)
                if monster is None:
                    errors.append(f"floors.json: B{floor_number}F: 敵 {monster_id} がありません")
                elif not monster.first_floor <= floor_number <= monster.last_floor:
                    errors.append(
                        f"floors.json: B{floor_number}F: {monster_id} の出現階の範囲外です"
                    )
        if errors:
            raise DataValidationError("\n".join(errors))


def _by_id(definitions: list[Any], source: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for definition in definitions:
        if definition.id in result:
            raise DataValidationError(f"{source}: ID が重複しています: {definition.id}")
        result[definition.id] = definition
    return result
