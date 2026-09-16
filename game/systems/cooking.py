"""食材ドロップ・腐敗・レシピ照合・手帳。仕様書 9章。

pyxel を import しないこと。
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from game.data_loader import DataValidationError, dataclass_from_dict
from game.entities.item import (
    CATEGORY_COOKED,
    CATEGORY_DISH,
    CATEGORY_FOOD,
    CATEGORY_INGREDIENT,
    Effect,
    ItemDef,
)
from game.systems.combat import round_half_up

PERCENT = 100
MIN_MATERIALS = 2
MAX_MATERIALS = 3
DISH_SPRITE = "item_dish"

HEAT_CAMPFIRE = "campfire"
HEAT_STOVE = "stove"


@dataclass(frozen=True)
class CutinSettings:
    """料理カットインの時間（秒）。balance.json の "cooking" → "cutin" で定義する。"""

    wipe_seconds: float
    cooking_seconds: float
    short_cooking_seconds: float
    short_cooking: bool  # 調理演出を短縮する
    skip_wipe: bool  # 切り替えと復帰のワイプを省略する

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CutinSettings:
        return dataclass_from_dict(cls, data, "cooking.cutin")


@dataclass(frozen=True)
class CookingParams:
    """料理・食材のパラメータ。balance.json の "cooking" で定義する。"""

    drop_chance: int
    rot_turns: int
    fail_chance: int
    campfire_chance: int
    campfire_floors: tuple[int, ...]  # 必ず焚き火を置く階
    memo_gold: int  # 先人のメモで、未発見のレシピがないときにもらえるお金
    mystery_penalties: tuple[Effect, ...]  # 謎の物体を食べたときのペナルティ（1つを均等に選ぶ）
    cutin: CutinSettings

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CookingParams:
        required = (
            "drop_chance", "rot_turns", "fail_chance", "campfire_chance", "campfire_floors",
            "memo_gold", "mystery_penalties", "cutin",
        )  # fmt: skip
        missing = [key for key in required if key not in data]
        if missing:
            raise DataValidationError(f"cooking: 必須キーがありません: {', '.join(missing)}")
        return cls(
            drop_chance=int(data["drop_chance"]),
            rot_turns=int(data["rot_turns"]),
            fail_chance=int(data["fail_chance"]),
            campfire_chance=int(data["campfire_chance"]),
            campfire_floors=tuple(int(f) for f in data["campfire_floors"]),
            memo_gold=int(data["memo_gold"]),
            mystery_penalties=tuple(Effect.from_dict(e) for e in data["mystery_penalties"]),
            cutin=CutinSettings.from_dict(data["cutin"]),
        )


# --- 食材 ---


def ingredient_items(data: Mapping[str, Any]) -> list[ItemDef]:
    """ingredients.json から、生の食材・焼き〇〇・腐った肉のアイテム定義を作る。"""
    source = "ingredients.json"
    rotten = dict(data["rotten"])
    items = [ItemDef.from_dict({**rotten, "category": CATEGORY_FOOD}, source)]
    for entry in data["ingredients"]:
        grilled = entry.get("grilled")
        description = data["raw_description"]
        if entry.get("rots"):
            description += "時間がたつと腐る。"
        items.append(
            ItemDef.from_dict(
                {
                    **entry,
                    "category": CATEGORY_INGREDIENT,
                    "description": entry.get("description", description),
                    "effects": data["raw_effects"],
                    "rotten_id": rotten["id"] if entry.get("rots") else None,
                    "grilled_id": grilled["id"] if grilled else None,
                },
                source,
            )
        )
        if grilled:
            items.append(
                ItemDef.from_dict(
                    {
                        "id": grilled["id"],
                        "name": grilled["name"],
                        "category": CATEGORY_COOKED,
                        "sprite": grilled.get("sprite", "item_grilled_meat"),
                        "tags": entry.get("tags", ()),
                        "description": data["grilled_description"],
                        "effects": data["grilled_effects"],
                    },
                    source,
                )
            )
    return items


def ingredient_drop_chance(base: int, multiplier: float, *, guaranteed: bool) -> int:
    """食材のドロップ率（%）。ナイフで 1.5倍、「解体術」で倒すと必ず落とす。"""
    if guaranteed:
        return PERCENT
    return min(PERCENT, round_half_up(base * multiplier))


# --- レシピ ---


@dataclass(frozen=True)
class IngredientSpec:
    """レシピの材料1つ分。食材ID かタグのどちらかで指定する。"""

    id: str | None = None
    tag: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], recipe_id: str) -> IngredientSpec:
        if ("id" in data) == ("tag" in data):
            raise DataValidationError(
                f"recipes.json: {recipe_id}: 材料は id か tag のどちらか1つで指定してください"
            )
        return cls(id=data.get("id"), tag=data.get("tag"))

    def matches(self, item: ItemDef) -> bool:
        if self.id is not None:
            return item.id == self.id
        return self.tag in item.tags


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    ingredients: tuple[IngredientSpec, ...]
    effects: tuple[Effect, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Recipe:
        missing = [key for key in ("id", "name", "ingredients", "effects") if key not in data]
        if missing:
            raise DataValidationError(
                f"recipes.json: {data.get('id', '?')}: 必須キーがありません: {', '.join(missing)}"
            )
        recipe_id = str(data["id"])
        ingredients = tuple(IngredientSpec.from_dict(i, recipe_id) for i in data["ingredients"])
        if not MIN_MATERIALS <= len(ingredients) <= MAX_MATERIALS:
            raise DataValidationError(f"recipes.json: {recipe_id}: 材料は2〜3個にしてください")
        return cls(
            id=recipe_id,
            name=str(data["name"]),
            ingredients=ingredients,
            effects=tuple(Effect.from_dict(e) for e in data["effects"]),
        )

    @property
    def id_count(self) -> int:
        return sum(1 for spec in self.ingredients if spec.id is not None)

    @property
    def uses_tags(self) -> bool:
        return self.id_count < len(self.ingredients)


def combination_key(materials: Iterable[ItemDef]) -> tuple[str, ...]:
    """材料の組み合わせ。順序を区別しないよう、ID を並べ替えて持つ。"""
    return tuple(sorted(m.id for m in materials))


def match_recipe(materials: Sequence[ItemDef], recipes: Iterable[Recipe]) -> Recipe | None:
    """材料に一致するレシピ。仕様書 9.4。

    材料の順序は区別しない。すべて ID で指定したレシピを先に、次にタグ指定を含むレシピを
    ID 指定の多い順に照合する（同じ優先度なら recipes.json の順）。
    """
    candidates = [r for r in recipes if len(r.ingredients) == len(materials)]
    candidates.sort(key=lambda r: (r.uses_tags, -r.id_count))
    for recipe in candidates:
        for ordered in itertools.permutations(materials):
            pairs = zip(recipe.ingredients, ordered, strict=True)
            if all(spec.matches(item) for spec, item in pairs):
                return recipe
    return None


def dish_item(recipe: Recipe, status_names: Mapping[str, str]) -> ItemDef:
    """レシピからできる料理のアイテム定義。"""
    return ItemDef(
        id=recipe.id,
        name=recipe.name,
        category=CATEGORY_DISH,
        sprite=DISH_SPRITE,
        description=f"{describe_effects(recipe.effects, status_names)}。",
        effects=recipe.effects,
    )


def describe_effects(effects: Iterable[Effect], status_names: Mapping[str, str]) -> str:
    """「満腹度+40、HP+20」のような効果の説明。"""
    parts: list[str] = []
    for effect in effects:
        names = "・".join(status_names.get(s, s) for s in effect.statuses)
        if effect.type == "satiety":
            parts.append(f"満腹度{effect.value:+d}")
        elif effect.type == "heal":
            parts.append(f"HP+{effect.value}")
        elif effect.type == "restore_mp":
            parts.append(f"MP+{effect.value}")
        elif effect.type == "restore_mp_full":
            parts.append("MP全回復")
        elif effect.type == "max_hp_up":
            parts.append(f"最大HP+{effect.value}（永続）")
        elif effect.type == "status":
            parts.append(names)
        elif effect.type == "cure":
            parts.append(f"{names}を解除")
    return "、".join(parts)


# --- 手帳 ---


@dataclass
class Notebook:
    """レシピ手帳。発見したレシピと、失敗した組み合わせを記録する。死亡しても消えない。"""

    discovered: list[str] = field(default_factory=list)  # 発見した順
    failures: list[tuple[str, ...]] = field(default_factory=list)

    def is_discovered(self, recipe_id: str) -> bool:
        return recipe_id in self.discovered

    def discover(self, recipe_id: str) -> bool:
        """登録する。新しく登録したら True。"""
        if recipe_id in self.discovered:
            return False
        self.discovered.append(recipe_id)
        return True

    def is_failure(self, key: tuple[str, ...]) -> bool:
        return key in self.failures

    def record_failure(self, key: tuple[str, ...]) -> bool:
        if key in self.failures:
            return False
        self.failures.append(key)
        return True


@dataclass(frozen=True)
class CookingPreview:
    """調理画面での予告表示。"""

    dish_name: str | None = None  # 手帳にある組み合わせなら料理名
    known_failure: bool = False  # 失敗リストにある組み合わせ


def preview(
    materials: Sequence[ItemDef], recipes: Iterable[Recipe], notebook: Notebook
) -> CookingPreview:
    if not MIN_MATERIALS <= len(materials) <= MAX_MATERIALS:
        return CookingPreview()
    if notebook.is_failure(combination_key(materials)):
        return CookingPreview(known_failure=True)
    recipe = match_recipe(materials, recipes)
    if recipe is not None and notebook.is_discovered(recipe.id):
        return CookingPreview(dish_name=recipe.name)
    return CookingPreview()
