"""迷宮の行商人のテスト。仕様書 12.4。"""

import pytest

from game.entities.item import ItemInstance
from game.systems import merchant
from game.systems.status import AILMENT
from tests.test_game_state import CATALOG, PARAMS, new_state

SPAWN = PARAMS.spawn
CURSE = PARAMS.equipment.curses[0]


def herb_def():
    return CATALOG.items["herb"]


def cursed_katana():
    """呪い付きの装備。生成は乱数任せなので、テストでは呪いを直に指定して作る。"""
    return ItemInstance(CATALOG.items["katana"], curse=CURSE, curse_known=True)


# --- 出現 ---


def test_merchant_always_appears_on_the_floor_before_a_boss():
    """ボス階の1つ手前には必ず現れる。"""
    for floor_number in SPAWN.merchant_floors:
        state = new_state()
        state.enter_floor(floor_number)
        assert state.floor.merchants, f"B{floor_number}F に行商人がいない"


def test_merchant_is_reachable_only_from_next_to_it():
    state = new_state()
    state.enter_floor(SPAWN.merchant_floors[0])
    m = state.floor.merchants[0]
    state.player.x, state.player.y = m.x - 1, m.y
    assert state.can_talk is True
    state.player.x, state.player.y = m.x - 3, m.y
    assert state.can_talk is False


def test_monsters_never_step_onto_the_merchant():
    state = new_state()
    state.enter_floor(SPAWN.merchant_floors[0])
    m = state.floor.merchants[0]
    assert state.is_free_for_monster(*m.pos) is False


# --- 買う ---


def test_merchant_sells_only_consumables_and_charges_more_than_the_camp():
    stock = merchant.stock(CATALOG.items, SPAWN)
    assert stock, "品揃えが空"
    assert all(d.category in merchant.CONSUMABLES for d in stock)
    herb = herb_def()
    assert merchant.price_of(herb, SPAWN) > (herb.price or 0)


def test_buying_spends_the_gold_carried_in_the_dungeon():
    state = new_state()
    state.player.gold = 1000
    before = len(state.inventory.items)
    message = merchant.buy(state.player, state.inventory, herb_def(), SPAWN)
    assert "買った" in message
    assert state.player.gold == 1000 - merchant.price_of(herb_def(), SPAWN)
    assert len(state.inventory.items) == before + 1


def test_cannot_buy_without_enough_gold():
    state = new_state()
    state.player.gold = 0
    assert merchant.buy(state.player, state.inventory, herb_def(), SPAWN) == "お金が足りない。"
    assert state.inventory.items == []


# --- 解毒 ---


def test_curing_removes_every_ailment_but_keeps_buffs():
    state = new_state()
    state.player.gold = 1000
    state._inflict_player("poison")
    state._inflict_player("blind")
    state.player.statuses.add(CATALOG.statuses["atk_up"])
    message = merchant.cure(state.player, CATALOG.statuses, SPAWN)
    assert "治った" in message
    assert "poison" not in state.player.statuses
    assert "blind" not in state.player.statuses
    assert "atk_up" in state.player.statuses  # バフは残る
    assert state.player.gold == 1000 - SPAWN.merchant_cure_cost


def test_curing_restores_max_hp_lost_to_the_ailment():
    state = new_state()
    state.player.gold = 1000
    before = state.player.max_hp
    state._inflict_player("max_hp_down")
    assert state.player.max_hp < before
    merchant.cure(state.player, CATALOG.statuses, SPAWN)
    assert state.player.max_hp == before


def test_curing_nothing_costs_nothing():
    state = new_state()
    state.player.gold = 1000
    assert merchant.cure(state.player, CATALOG.statuses, SPAWN) == "治すものがない。"
    assert state.player.gold == 1000


def test_ailments_lists_only_bad_statuses():
    state = new_state()
    state._inflict_player("poison")
    state.player.statuses.add(CATALOG.statuses["haste"])
    found = merchant.ailments(state.player, CATALOG.statuses)
    assert [d.id for d in found] == ["poison"]
    assert all(d.kind == AILMENT for d in found)


# --- 解呪 ---


def test_uncursing_frees_stuck_equipment():
    state = new_state()
    state.player.gold = 1000
    item = cursed_katana()
    message = merchant.uncurse(state.player, item, SPAWN)
    assert "呪いが解けた" in message
    assert item.cursed is False
    assert item.curse_known is True
    assert state.player.gold == 1000 - SPAWN.merchant_uncurse_cost


def test_uncursing_an_uncursed_item_costs_nothing():
    state = new_state()
    state.player.gold = 1000
    item = ItemInstance(CATALOG.items["katana"])
    assert "呪われていない" in merchant.uncurse(state.player, item, SPAWN)
    assert state.player.gold == 1000


@pytest.mark.parametrize("gold", [0, 299])
def test_cannot_uncurse_without_enough_gold(gold):
    state = new_state()
    state.player.gold = gold
    item = cursed_katana()
    assert merchant.uncurse(state.player, item, SPAWN) == "お金が足りない。"
    assert item.cursed is True
