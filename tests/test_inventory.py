from game import data_loader
from game.entities.item import ItemInstance
from game.systems.catalog import Catalog
from game.systems.inventory import Inventory

CATALOG = Catalog.from_data(data_loader.load_all())
HERB = CATALOG.items["herb"]
ARROW = CATALOG.items["arrow"]


def test_add_until_capacity():
    inventory = Inventory(capacity=3, stack_max=99)
    for _ in range(3):
        assert inventory.add(ItemInstance(HERB))
    assert inventory.is_full
    extra = ItemInstance(HERB)
    assert not inventory.can_add(extra)
    assert not inventory.add(extra)
    assert len(inventory) == 3


def test_arrows_stack_up_to_limit_per_slot():
    inventory = Inventory(capacity=5, stack_max=99)
    inventory.add(ItemInstance(ARROW, 95))
    inventory.add(ItemInstance(ARROW, 10))
    assert [item.count for item in inventory.items] == [99, 6]
    assert inventory.items[0].name == "矢（99本）"


def test_arrows_merge_into_existing_stack_even_when_full():
    inventory = Inventory(capacity=1, stack_max=99)
    inventory.add(ItemInstance(ARROW, 50))
    assert inventory.is_full
    assert inventory.add(ItemInstance(ARROW, 49))
    assert not inventory.add(ItemInstance(ARROW, 1))
    assert inventory.items[0].count == 99


def test_take_one_splits_stack_and_frees_slot():
    inventory = Inventory(capacity=5, stack_max=99)
    inventory.add(ItemInstance(ARROW, 2))
    arrow = inventory.items[0]
    one = inventory.take_one(arrow)
    assert one.count == 1 and arrow.count == 1
    inventory.take_one(arrow)
    assert len(inventory) == 0


def test_find_by_id():
    inventory = Inventory(capacity=5, stack_max=99)
    herb = ItemInstance(HERB)
    inventory.add(herb)
    assert inventory.find("herb") is herb
    assert inventory.find("arrow") is None
