"""拠点（ベースキャンプ）の施設と、死亡・生還の引き継ぎのテスト（フェーズ6）。仕様書 12.3。"""

from game import data_loader
from game.entities.item import SLOT_WEAPON, SLOTS, EquipmentTrait, ItemInstance
from game.systems import meta as meta_system
from game.systems.catalog import Catalog
from game.systems.meta import BaseCampParams, MetaProgress

DATA = data_loader.load_all()
CATALOG = Catalog.from_data(DATA)
CAMP = BaseCampParams.from_dict(DATA["balance"]["base_camp"])
CAPACITY = int(DATA["balance"]["inventory"]["capacity"])
STACK = int(DATA["balance"]["inventory"]["stack_max"])
CURSE = DATA["balance"]["equipment"]["curses"][0]


def new_meta(funds: int = 0) -> MetaProgress:
    meta = MetaProgress.new(CAPACITY, STACK, CAMP)
    meta.funds = funds
    return meta


def item(item_id: str, **changes) -> ItemInstance:
    return ItemInstance(CATALOG.items[item_id], **changes)


def cursed_knife() -> ItemInstance:
    return item("knife", curse=EquipmentTrait.from_dict(CURSE))


# --- 道具屋 ---


def test_shop_sells_only_items_with_a_price():
    ids = {definition.id for definition in meta_system.shop_items(CATALOG.items)}
    assert "herb" in ids and "knife" in ids  # 消費アイテムと基本装備
    assert "katana" not in ids and "gold" not in ids  # レア装備と非売品は並べない


def test_buying_spends_funds_and_gives_the_item():
    meta = new_meta(funds=200)
    message = meta_system.buy(meta, CAMP, CATALOG.items["herb"])
    assert meta.funds == 200 - CATALOG.items["herb"].price
    assert [i.id for i in meta.loadout.items.items] == ["herb"]
    assert "買った" in message


def test_arrows_are_sold_in_bundles():
    meta = new_meta(funds=200)
    meta_system.buy(meta, CAMP, CATALOG.items["arrow"])
    assert meta.loadout.items.items[0].count == CAMP.bundles["arrow"]


def test_buying_without_funds_changes_nothing():
    meta = new_meta(funds=10)
    assert meta_system.buy(meta, CAMP, CATALOG.items["herb"]) == "お金が足りない。"
    assert meta.funds == 10 and not meta.loadout.items.items


# --- 鑑定屋・解呪屋 ---


def test_appraising_costs_money_and_reveals_the_item():
    meta = new_meta(funds=CAMP.appraise_cost)
    spear = item("spear", modifier=2, identified=False, curse_known=False)
    meta.loadout.items.add(spear)
    meta_system.appraise(meta, CAMP, spear)
    assert spear.identified and spear.curse_known
    assert meta.funds == 0


def test_uncursing_removes_the_curse_and_unequips():
    meta = new_meta(funds=CAMP.uncurse_cost)
    knife = cursed_knife()
    meta.loadout.items.add(knife)
    meta.loadout.equipment[SLOT_WEAPON] = knife
    message = meta_system.uncurse(meta, CAMP, knife)
    assert not knife.cursed
    assert meta.loadout.equipment[SLOT_WEAPON] is None
    assert meta.funds == 0 and "呪いが解けた" in message


def test_uncursing_an_uncursed_item_is_free():
    meta = new_meta(funds=CAMP.uncurse_cost)
    knife = item("knife")
    meta.loadout.items.add(knife)
    assert "呪われていない" in meta_system.uncurse(meta, CAMP, knife)
    assert meta.funds == CAMP.uncurse_cost


# --- 倉庫・拡張 ---


def test_storage_keeps_items_between_runs():
    meta = new_meta()
    herb = item("herb")
    meta.loadout.items.add(herb)
    meta_system.deposit(meta, herb)
    assert [i.id for i in meta.storage.items] == ["herb"]
    assert not meta.loadout.items.items

    meta_system.withdraw(meta, herb)
    assert not meta.storage.items
    assert [i.id for i in meta.loadout.items.items] == ["herb"]


def test_cursed_equipment_cannot_be_deposited():
    meta = new_meta()
    knife = cursed_knife()
    meta.loadout.items.add(knife)
    meta.loadout.equipment[SLOT_WEAPON] = knife
    assert "外せない" in meta_system.deposit(meta, knife)
    assert meta.loadout.items.items == [knife]


def test_expansions_are_limited():
    expansion = CAMP.inventory_expansion
    meta = new_meta(funds=expansion.cost * (expansion.max_times + 1))
    for times in range(expansion.max_times):
        meta_system.expand_inventory(meta, CAMP)
        assert meta.loadout.items.capacity == CAPACITY + expansion.amount * (times + 1)
    assert "これ以上" in meta_system.expand_inventory(meta, CAMP)
    assert meta.inventory_expansions == expansion.max_times


# --- 引き継ぎ（仕様書 12.3） ---


def carried(meta: MetaProgress) -> list[str]:
    return [i.id for i in meta.loadout.items.items]


def test_surviving_keeps_items_and_adds_gold_to_the_funds():
    meta = new_meta(funds=100)
    knife, herb = item("knife"), item("herb")
    equipment = dict.fromkeys(SLOTS) | {SLOT_WEAPON: knife}
    meta.finish_run(
        survived=True, items=[knife, herb], equipment=equipment, gold=250, floor_number=4
    )
    assert meta.funds == 350
    assert carried(meta) == ["knife", "herb"]
    assert meta.loadout.equipment[SLOT_WEAPON] is knife  # 装備したまま持ち帰る
    assert meta.deepest_floor == 4


def test_dying_loses_items_and_gold_but_keeps_the_record():
    meta = new_meta(funds=100)
    meta.storage.add(item("herb"))
    meta.notebook.discover("rat_skewer")
    meta.finish_run(
        survived=False,
        items=[item("knife")],
        equipment=dict.fromkeys(SLOTS),
        gold=250,
        floor_number=7,
    )
    assert meta.funds == 100  # 挑戦中の所持金は失う
    assert carried(meta) == []
    assert [i.id for i in meta.storage.items] == ["herb"]  # 倉庫は残る
    assert meta.notebook.is_discovered("rat_skewer")  # 手帳も残る
    assert meta.deepest_floor == 7


def test_deepest_floor_never_goes_back():
    meta = new_meta()
    meta.record_run(9)
    meta.record_run(3)
    assert meta.deepest_floor == 9
