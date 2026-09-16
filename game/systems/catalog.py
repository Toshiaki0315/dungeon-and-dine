"""data/ の定義（敵・アイテム・食材・レシピ・罠・状態異常・スキル）を読み込み、相互参照を検証する。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import DataValidationError
from game.entities.item import (
    CATEGORY_ARMOR,
    CATEGORY_WEAPON,
    CHEST_CLOSED_SPRITE,
    CHEST_OPEN_SPRITE,
    GOLD_ID,
    MYSTERY_FOOD_ID,
    ItemDef,
    WeaponStats,
)
from game.entities.monster import ABILITY_ON_HIT_STATUS, MonsterDef
from game.systems.combat import REACHES
from game.systems.cooking import Recipe, dish_item, ingredient_items
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
    items: Mapping[str, ItemDef]  # 武器・防具・食材・料理も含む
    unarmed: WeaponStats
    traps: Mapping[str, TrapDef]
    statuses: Mapping[str, StatusDef]
    skills: Mapping[str, SkillDef]
    recipes: Mapping[str, Recipe]  # recipes.json の順
    spawn_tables: Mapping[int, Mapping[str, int]]  # 階層 → 敵ID → 出現の重み

    @classmethod
    def from_data(cls, data: Mapping[str, Mapping[str, Any]]) -> Catalog:
        statuses = _by_id(
            [StatusDef.from_dict(d) for d in data["status_effects"]["status_effects"]],
            "status_effects.json",
        )
        recipes = _by_id([Recipe.from_dict(d) for d in data["recipes"]["recipes"]], "recipes.json")
        status_names = {s.id: s.name for s in statuses.values()}

        item_defs = [ItemDef.from_dict(d, "items.json") for d in data["items"]["items"]]
        item_defs += [
            ItemDef.from_dict({**d, "category": CATEGORY_WEAPON}, "weapons.json")
            for d in data["weapons"]["weapons"]
        ]
        item_defs += [
            ItemDef.from_dict({**d, "category": CATEGORY_ARMOR}, "armors.json")
            for d in data["armors"]["armors"]
        ]
        item_defs += ingredient_items(data["ingredients"])
        item_defs += [dish_item(recipe, status_names) for recipe in recipes.values()]

        catalog = cls(
            monsters=_by_id(
                [MonsterDef.from_dict(d) for d in data["enemies"]["enemies"]], "enemies.json"
            ),
            items=_by_id(item_defs, "items.json / weapons.json / armors.json / ingredients.json"),
            unarmed=WeaponStats.from_dict(data["weapons"]["unarmed"]),
            traps=_by_id([TrapDef.from_dict(d) for d in data["traps"]["traps"]], "traps.json"),
            statuses=statuses,
            skills=_by_id([SkillDef.from_dict(d) for d in data["skills"]["skills"]], "skills.json"),
            recipes=recipes,
            spawn_tables={
                int(entry["floor"]): {str(k): int(v) for k, v in entry["monsters"].items()}
                for entry in data["floors"]["floors"]
            },
        )
        catalog._validate()
        return catalog

    def spawn_table(self, floor_number: int) -> Mapping[str, int]:
        return self.spawn_tables.get(floor_number, {})

    def sprite_names(self) -> set[str]:
        """敵・アイテム・宝箱・罠の定義が参照する sprites.json のキー。"""
        names = {CHEST_CLOSED_SPRITE, CHEST_OPEN_SPRITE}
        names.update(m.sprite for m in self.monsters.values())
        names.update(i.sprite for i in self.items.values())
        names.update(t.sprite for t in self.traps.values())
        return names

    def ingredient_label(self, recipe: Recipe) -> str:
        """「ネズミ肉＋薬草」「〈肉類〉＋〈キノコ類〉＋岩塩」のような材料の表記。"""
        return "＋".join(
            self.items[spec.id].name if spec.id is not None else f"〈{spec.tag}〉"
            for spec in recipe.ingredients
        )

    def _validate(self) -> None:
        errors: list[str] = [
            f"status_effects.json: {s} がありません"
            for s in REQUIRED_STATUSES
            if s not in self.statuses
        ]
        errors += [
            f"items.json: {item_id} がありません"
            for item_id in (GOLD_ID, MYSTERY_FOOD_ID)
            if item_id not in self.items
        ]
        for monster in self.monsters.values():
            for ability in monster.abilities:
                if ability.type == ABILITY_ON_HIT_STATUS and ability.status not in self.statuses:
                    errors.append(
                        f"enemies.json: {monster.id}: 状態異常 {ability.status} がありません"
                    )
            if monster.drop is not None and monster.drop not in self.items:
                errors.append(f"enemies.json: {monster.id}: 食材 {monster.drop} がありません")
        for item in self.items.values():
            if item.weapon is not None and item.weapon.reach not in REACHES:
                errors.append(f"weapons.json: {item.id}: 攻撃範囲 {item.weapon.reach} が不正です")
            for effect in item.effects:
                errors += [
                    f"{item.id}: 効果の状態異常 {s} がありません"
                    for s in effect.statuses
                    if s not in self.statuses
                ]
            errors += [
                f"ingredients.json: {item.id}: {ref} がありません"
                for ref in (item.rotten_id, item.grilled_id)
                if ref is not None and ref not in self.items
            ]
        tags = {tag for item in self.items.values() for tag in item.tags}
        for recipe in self.recipes.values():
            for spec in recipe.ingredients:
                if spec.id is not None and spec.id not in self.items:
                    errors.append(f"recipes.json: {recipe.id}: 材料 {spec.id} がありません")
                if spec.tag is not None and spec.tag not in tags:
                    errors.append(f"recipes.json: {recipe.id}: タグ {spec.tag} の食材がありません")
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
