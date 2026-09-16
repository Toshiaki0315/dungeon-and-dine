"""レシピ照合・手帳・食材の定義のテスト（フェーズ5）。"""

from game import data_loader
from game.entities.item import CATEGORY_COOKED, CATEGORY_DISH, CATEGORY_INGREDIENT
from game.systems.catalog import Catalog
from game.systems.cooking import (
    CookingParams,
    IngredientSpec,
    Notebook,
    Recipe,
    combination_key,
    describe_effects,
    ingredient_drop_chance,
    match_recipe,
    preview,
)

DATA = data_loader.load_all()
CATALOG = Catalog.from_data(DATA)
RECIPES = list(CATALOG.recipes.values())
PARAMS = CookingParams.from_dict(DATA["balance"]["cooking"])
STATUS_NAMES = {s.id: s.name for s in CATALOG.statuses.values()}


def materials_for(recipe):
    """レシピを満たす材料。タグ指定には、そのタグを持つ食材を1つ選ぶ。"""
    materials = []
    for spec in recipe.ingredients:
        if spec.id is not None:
            materials.append(CATALOG.items[spec.id])
        else:
            materials.append(next(i for i in CATALOG.items.values() if spec.tag in i.tags))
    return materials


# --- 照合（仕様書 9.4） ---


def test_every_recipe_matches_its_own_ingredients():
    for recipe in RECIPES:
        assert match_recipe(materials_for(recipe), RECIPES) is recipe


def test_order_of_materials_does_not_matter():
    for recipe in RECIPES:
        materials = materials_for(recipe)
        assert match_recipe(list(reversed(materials)), RECIPES) is recipe


def test_unknown_combination_has_no_recipe():
    herb = CATALOG.items["herb"]
    assert match_recipe([herb, herb], RECIPES) is None


def test_id_recipes_are_preferred_over_tag_recipes():
    salt = IngredientSpec(id="rock_salt")
    tag_recipe = Recipe("stew", "ごった煮", (IngredientSpec(tag="肉類"), salt), ())
    id_recipe = Recipe("roast", "焼き肉", (IngredientSpec(id="rat_meat"), salt), ())
    materials = [CATALOG.items["rat_meat"], CATALOG.items["rock_salt"]]
    assert match_recipe(materials, [tag_recipe, id_recipe]) is id_recipe


def test_recipes_with_more_id_ingredients_are_preferred():
    salt = IngredientSpec(id="rock_salt")
    fewer = Recipe("a", "A", (IngredientSpec(tag="肉類"), IngredientSpec(tag="調味料")), ())
    more = Recipe("b", "B", (IngredientSpec(tag="肉類"), salt), ())
    materials = [CATALOG.items["rat_meat"], CATALOG.items["rock_salt"]]
    assert match_recipe(materials, [fewer, more]) is more


def test_combination_key_ignores_order():
    herb, meat = CATALOG.items["herb"], CATALOG.items["rat_meat"]
    assert combination_key([herb, meat]) == combination_key([meat, herb]) == ("herb", "rat_meat")


# --- 食材（仕様書 9.1 / 9.2） ---


def test_ingredient_drop_chance_follows_the_weapon():
    assert ingredient_drop_chance(30, 1.0, guaranteed=False) == 30
    assert ingredient_drop_chance(30, 1.5, guaranteed=False) == 45  # ナイフ
    assert ingredient_drop_chance(30, 1.0, guaranteed=True) == 100  # 解体術
    assert ingredient_drop_chance(80, 1.5, guaranteed=False) == 100  # 100% を超えない


def test_raw_meat_rots_and_grilled_meat_does_not():
    meat = CATALOG.items["rat_meat"]
    assert meat.category == CATEGORY_INGREDIENT
    assert meat.rotten_id == "rotten_meat" and meat.rotten_id in CATALOG.items
    grilled = CATALOG.items[meat.grilled_id]
    assert grilled.category == CATEGORY_COOKED
    assert grilled.rotten_id is None and grilled.tags == meat.tags


def test_eating_a_raw_ingredient_can_cause_poison():
    effects = {e.type: e for e in CATALOG.items["rat_meat"].effects}
    assert effects["satiety"].value == 10
    assert effects["inflict"].statuses == ("poison",) and effects["inflict"].chance == 30


def test_dish_items_are_created_from_recipes():
    for recipe in RECIPES:
        dish = CATALOG.items[recipe.id]
        assert dish.category == CATEGORY_DISH
        assert dish.name == recipe.name and dish.effects == recipe.effects


# --- 手帳（仕様書 9.6） ---


def test_notebook_records_discoveries_and_failures():
    notebook = Notebook()
    assert notebook.discover("rat_skewer") is True
    assert notebook.discover("rat_skewer") is False  # 二重には登録しない
    assert notebook.is_discovered("rat_skewer")
    key = ("bone", "herb")
    assert notebook.record_failure(key) is True
    assert notebook.record_failure(key) is False
    assert notebook.is_failure(key)


def test_preview_shows_known_dishes_and_failures():
    notebook = Notebook()
    materials = materials_for(CATALOG.recipes["rat_skewer"])
    assert preview(materials, RECIPES, notebook).dish_name is None  # 未発見は予告しない
    notebook.discover("rat_skewer")
    assert preview(materials, RECIPES, notebook).dish_name == "ネズミ肉の串焼き"

    failed = [CATALOG.items["herb"], CATALOG.items["herb"]]
    notebook.record_failure(combination_key(failed))
    assert preview(failed, RECIPES, notebook).known_failure is True


def test_preview_needs_two_or_three_materials():
    notebook = Notebook()
    notebook.discover("rat_skewer")
    materials = materials_for(CATALOG.recipes["rat_skewer"])
    assert preview(materials[:1], RECIPES, notebook).dish_name is None


def test_describe_effects_reads_like_the_specification():
    text = describe_effects(CATALOG.recipes["rat_skewer"].effects, STATUS_NAMES)
    assert text == "満腹度+40、HP+20"
    soup = describe_effects(CATALOG.recipes["purifying_soup"].effects, STATUS_NAMES)
    assert soup == "満腹度+30、MP全回復、状態異常耐性、最大HP減少を解除"


def test_mystery_penalties_are_defined():
    assert len(PARAMS.mystery_penalties) == 4
