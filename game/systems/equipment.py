"""装備の生成（修正値・印・呪い）と、ステータスへの反映。仕様書 10章。

pyxel を import しないこと。
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import DataValidationError
from game.entities.item import SLOT_NAMES, EquipmentTrait, ItemDef, ItemInstance
from game.rng import weighted_choice

PERCENT = 100


@dataclass(frozen=True)
class EquipmentParams:
    """装備の生成パラメータ。balance.json の "equipment" で定義する。"""

    modifier_weights: Mapping[int, int]
    mark_chance: int
    curse_chance: int
    deep_curse_chance: int
    deep_curse_floor: int  # この階層以降は deep_curse_chance を使う
    cursed_modifier_min: int
    cursed_modifier_max: int
    marks: tuple[EquipmentTrait, ...]
    curses: tuple[EquipmentTrait, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EquipmentParams:
        required = (
            "modifier_weights", "mark_chance", "curse_chance", "deep_curse_chance",
            "deep_curse_floor", "cursed_modifier_min", "cursed_modifier_max", "marks", "curses",
        )  # fmt: skip
        missing = [key for key in required if key not in data]
        if missing:
            raise DataValidationError(f"equipment: 必須キーがありません: {', '.join(missing)}")
        return cls(
            modifier_weights={int(k): int(v) for k, v in data["modifier_weights"].items()},
            mark_chance=int(data["mark_chance"]),
            curse_chance=int(data["curse_chance"]),
            deep_curse_chance=int(data["deep_curse_chance"]),
            deep_curse_floor=int(data["deep_curse_floor"]),
            cursed_modifier_min=int(data["cursed_modifier_min"]),
            cursed_modifier_max=int(data["cursed_modifier_max"]),
            marks=tuple(EquipmentTrait.from_dict(m) for m in data["marks"]),
            curses=tuple(EquipmentTrait.from_dict(c) for c in data["curses"]),
        )

    def curse_chance_for(self, floor_number: int) -> int:
        if floor_number >= self.deep_curse_floor:
            return self.deep_curse_chance
        return self.curse_chance


def generate_equipment(
    definition: ItemDef, rng: random.Random, floor_number: int, params: EquipmentParams
) -> ItemInstance:
    """ダンジョンで拾う未鑑定の装備を作る。呪いの有無はここで決まる（仕様書 10.6）。"""
    curse: EquipmentTrait | None = None
    if params.curses and rng.randrange(100) < params.curse_chance_for(floor_number):
        curse = rng.choice(params.curses)
    if curse is not None:
        modifier = rng.randint(params.cursed_modifier_min, params.cursed_modifier_max)
    else:
        weights = {str(k): w for k, w in params.modifier_weights.items()}
        modifier = int(weighted_choice(rng, weights) or 0)
    mark = None
    if params.marks and rng.randrange(100) < params.mark_chance:
        mark = rng.choice(params.marks)
    return ItemInstance(
        definition,
        modifier=modifier,
        mark=mark,
        curse=curse,
        identified=False,
        curse_known=False,
    )


def attack_of(item: ItemInstance) -> int:
    weapon = item.definition.weapon
    return weapon.attack + item.modifier if weapon is not None else 0


def defense_of(item: ItemInstance) -> int:
    armor = item.definition.armor
    return armor.defense + item.modifier if armor is not None else 0


@dataclass(frozen=True)
class EquipmentBonus:
    """装備中の防具・印・呪いによる効果の合計（武器の攻撃力は含まない）。"""

    defense: int = 0
    crit_bonus: int = 0
    hit_percent: int = PERCENT
    block_rate: int = 0
    sight_bonus: int = 0
    status_resist: bool = False
    max_hp_bonus: int = 0
    trap_find_bonus: int = 0
    trap_avoid_rate: int = 0
    hunger_rate_percent: int = PERCENT
    cook_fail_bonus: int = 0
    fire_attack: bool = False
    skill_seal: bool = False
    no_trap_find: bool = False


def compute_bonus(equipment: Mapping[str, ItemInstance | None]) -> EquipmentBonus:
    defense = crit = block = sight = max_hp = trap_find = trap_avoid = cook_fail = 0
    hit = hunger = PERCENT
    status_resist = fire = skill_seal = no_trap_find = False
    for item in equipment.values():
        if item is None:
            continue
        armor = item.definition.armor
        if armor is not None:
            defense += defense_of(item)
            block = max(block, armor.block_rate)
            sight += armor.sight_bonus
            status_resist = status_resist or armor.status_resist
            max_hp += armor.max_hp_bonus
            trap_find += armor.trap_find_bonus
            trap_avoid = max(trap_avoid, armor.trap_avoid_rate)
            hunger = hunger * armor.hunger_rate_percent // PERCENT
        for trait in (item.mark, item.curse):
            if trait is None:
                continue
            crit += trait.crit_bonus
            hit = hit * trait.hit_percent // PERCENT
            hunger = hunger * trait.hunger_rate_percent // PERCENT
            sight += trait.sight_bonus
            cook_fail += trait.cook_fail_bonus
            fire = fire or trait.fire
            skill_seal = skill_seal or trait.skill_seal
            no_trap_find = no_trap_find or trait.no_trap_find
    return EquipmentBonus(
        defense=defense,
        crit_bonus=crit,
        hit_percent=hit,
        block_rate=block,
        sight_bonus=sight,
        status_resist=status_resist,
        max_hp_bonus=max_hp,
        trap_find_bonus=trap_find,
        trap_avoid_rate=trap_avoid,
        hunger_rate_percent=hunger,
        cook_fail_bonus=cook_fail,
        fire_attack=fire,
        skill_seal=skill_seal,
        no_trap_find=no_trap_find,
    )


def describe_equipment(item: ItemInstance) -> list[str]:
    """説明欄に出す性能。判明していない修正値・印・呪いは ??? と表示する。"""
    definition = item.definition
    assert definition.slot is not None
    kind = SLOT_NAMES[definition.slot]
    if definition.weapon is not None:
        lines = [f"{kind}  攻撃力 {definition.weapon.attack}"]
    else:
        assert definition.armor is not None
        lines = [f"{kind}  防御力 {definition.armor.defense}"]
    if item.identified:
        mark = item.mark.name if item.mark is not None else "なし"
        lines.append(f"修正値 {item.modifier:+d}  印 {mark}")
        lines.append(f"呪い {item.curse.name if item.curse is not None else 'なし'}")
    else:
        lines.append("修正値 ???  印 ???")
        if item.curse_known:
            lines.append(f"呪い {'あり' if item.cursed else 'なし'}")
        else:
            lines.append("呪い ???")
    return lines
