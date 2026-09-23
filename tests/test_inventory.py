from game import data_loader
from game.entities.item import ItemInstance
from game.systems.catalog import Catalog
from game.systems.inventory import Inventory

CATALOG = Catalog.from_data(data_loader.load_all())
HERB = CATALOG.items["herb"]
ARROW = CATALOG.items["arrow"]
KNIFE = CATALOG.items["knife"]
STOVE = CATALOG.items["stove"]
RAT_MEAT = CATALOG.items["rat_meat"]


def test_add_until_capacity():
    inventory = Inventory(capacity=3, stack_max=99, item_stack_max=1)
    for _ in range(3):
        assert inventory.add(ItemInstance(HERB))
    assert inventory.is_full
    extra = ItemInstance(HERB)
    assert not inventory.can_add(extra)
    assert not inventory.add(extra)
    assert len(inventory) == 3


def test_arrows_stack_up_to_limit_per_slot():
    inventory = Inventory(capacity=5, stack_max=99, item_stack_max=1)
    inventory.add(ItemInstance(ARROW, 95))
    inventory.add(ItemInstance(ARROW, 10))
    assert [item.count for item in inventory.items] == [99, 6]
    assert inventory.items[0].name == "矢（99本）"


def test_arrows_merge_into_existing_stack_even_when_full():
    inventory = Inventory(capacity=1, stack_max=99, item_stack_max=1)
    inventory.add(ItemInstance(ARROW, 50))
    assert inventory.is_full
    assert inventory.add(ItemInstance(ARROW, 49))
    assert not inventory.add(ItemInstance(ARROW, 1))
    assert inventory.items[0].count == 99


def test_take_one_splits_stack_and_frees_slot():
    inventory = Inventory(capacity=5, stack_max=99, item_stack_max=1)
    inventory.add(ItemInstance(ARROW, 2))
    arrow = inventory.items[0]
    one = inventory.take_one(arrow)
    assert one.count == 1 and arrow.count == 1
    inventory.take_one(arrow)
    assert len(inventory) == 0


def test_find_by_id():
    inventory = Inventory(capacity=5, stack_max=99, item_stack_max=1)
    herb = ItemInstance(HERB)
    inventory.add(herb)
    assert inventory.find("herb") is herb
    assert inventory.find("arrow") is None


# --- 同じ消耗品をまとめる（仕様書 11.1） ---


def test_same_consumables_share_a_slot_up_to_the_limit():
    inventory = Inventory(capacity=5, stack_max=99, item_stack_max=5)
    for _ in range(7):
        assert inventory.add(ItemInstance(HERB))
    assert [item.count for item in inventory.items] == [5, 2]
    assert inventory.items[0].name == "薬草×5"
    assert inventory.items[1].name == "薬草×2"


def test_a_full_inventory_still_accepts_items_that_fit_an_existing_stack():
    inventory = Inventory(capacity=1, stack_max=99, item_stack_max=5)
    inventory.add(ItemInstance(HERB, 4))
    assert inventory.add(ItemInstance(HERB))
    assert not inventory.add(ItemInstance(HERB))
    assert inventory.items[0].count == 5


def test_equipment_and_tools_with_charges_never_stack():
    inventory = Inventory(capacity=5, stack_max=99, item_stack_max=5)
    for definition in (KNIFE, KNIFE, STOVE, STOVE):
        inventory.add(ItemInstance(definition))
    assert [item.count for item in inventory.items] == [1, 1, 1, 1]


def test_stacked_raw_meat_rots_with_the_earliest_piece():
    inventory = Inventory(capacity=5, stack_max=99, item_stack_max=5)
    inventory.add(ItemInstance(RAT_MEAT, rot_at=900))
    inventory.add(ItemInstance(RAT_MEAT, rot_at=500))
    meat = inventory.items[0]
    assert (meat.count, meat.rot_at) == (2, 500)
    assert inventory.take_one(meat).rot_at == 500


def test_the_first_item_keeps_its_identity():
    inventory = Inventory(capacity=5, stack_max=99, item_stack_max=5)
    herb = ItemInstance(HERB)
    inventory.add(herb)
    inventory.add(ItemInstance(HERB))
    assert inventory.items == [herb] and herb.count == 2
