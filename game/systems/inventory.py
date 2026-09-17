"""インベントリ。仕様書 11.1。

pyxel を import しないこと。
"""

from __future__ import annotations

from game.entities.item import ItemInstance, stacks_in_inventory


class Inventory:
    def __init__(self, capacity: int, stack_max: int, item_stack_max: int = 1) -> None:
        self.capacity = capacity
        self.stack_max = stack_max  # 矢など、数を単位で扱うアイテムの1枠あたりの上限
        self.item_stack_max = item_stack_max  # 薬草・食材など、同じ消耗品の1枠あたりの上限
        self.items: list[ItemInstance] = []

    def __len__(self) -> int:
        return len(self.items)

    @property
    def is_full(self) -> bool:
        return len(self.items) >= self.capacity

    def stack_limit(self, item: ItemInstance) -> int:
        """1枠にまとめられる数。装備や携帯コンロなど、個体ごとに状態が違うものは1。"""
        if item.definition.stackable:
            return self.stack_max
        return self.item_stack_max if stacks_in_inventory(item.definition) else 1

    def can_add(self, item: ItemInstance) -> bool:
        return self._room_for(item) >= item.count

    def add(self, item: ItemInstance) -> bool:
        """全部入るときだけ追加する。入らなければ何もせず False を返す。"""
        if not self.can_add(item):
            return False
        limit = self.stack_limit(item)
        remaining = item.count
        for stack in self._stacks_of(item):
            moved = min(limit - stack.count, remaining)
            if moved <= 0:
                continue
            stack.count += moved
            stack.rot_at = _earlier(stack.rot_at, item.rot_at)
            remaining -= moved
        if remaining == item.count and remaining <= limit:
            self.items.append(item)  # まとめる先がなければ、渡された個体をそのまま入れる
            return True
        while remaining > 0:
            moved = min(limit, remaining)
            self.items.append(ItemInstance(item.definition, moved, rot_at=item.rot_at))
            remaining -= moved
        return True

    def remove(self, item: ItemInstance) -> None:
        self.items.remove(item)

    def take_one(self, item: ItemInstance) -> ItemInstance:
        """1個（1本）を取り出す。枠が空になったら取り除く。"""
        if item.count > 1:
            item.count -= 1
            return ItemInstance(item.definition, 1, rot_at=item.rot_at)
        self.items.remove(item)
        return item

    def find(self, item_id: str) -> ItemInstance | None:
        return next((item for item in self.items if item.id == item_id), None)

    def _stacks_of(self, item: ItemInstance) -> list[ItemInstance]:
        if self.stack_limit(item) <= 1:
            return []
        return [i for i in self.items if i.id == item.id and i is not item]

    def _room_for(self, item: ItemInstance) -> int:
        limit = self.stack_limit(item)
        free_slots = self.capacity - len(self.items)
        in_stacks = sum(max(0, limit - s.count) for s in self._stacks_of(item))
        return in_stacks + max(0, free_slots) * limit


def _earlier(a: int | None, b: int | None) -> int | None:
    """まとめた生肉は、早く腐るほうに揃える（1枠の中で腐る時間を分けて持てないため）。"""
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)
