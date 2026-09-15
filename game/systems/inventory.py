"""インベントリ。仕様書 11.1。

pyxel を import しないこと。
"""

from __future__ import annotations

from game.entities.item import ItemInstance


class Inventory:
    def __init__(self, capacity: int, stack_max: int) -> None:
        self.capacity = capacity
        self.stack_max = stack_max  # 矢など、まとめられるアイテムの1枠あたりの上限
        self.items: list[ItemInstance] = []

    def __len__(self) -> int:
        return len(self.items)

    @property
    def is_full(self) -> bool:
        return len(self.items) >= self.capacity

    def can_add(self, item: ItemInstance) -> bool:
        return self._room_for(item) >= item.count

    def add(self, item: ItemInstance) -> bool:
        """全部入るときだけ追加する。入らなければ何もせず False を返す。"""
        if not self.can_add(item):
            return False
        if not item.definition.stackable:
            self.items.append(item)
            return True

        remaining = item.count
        for stack in self._stacks_of(item.id):
            moved = min(self.stack_max - stack.count, remaining)
            stack.count += moved
            remaining -= moved
        while remaining > 0:
            moved = min(self.stack_max, remaining)
            self.items.append(ItemInstance(item.definition, moved))
            remaining -= moved
        return True

    def remove(self, item: ItemInstance) -> None:
        self.items.remove(item)

    def take_one(self, item: ItemInstance) -> ItemInstance:
        """1個（1本）を取り出す。枠が空になったら取り除く。"""
        if item.count > 1:
            item.count -= 1
            return ItemInstance(item.definition, 1)
        self.items.remove(item)
        return item

    def find(self, item_id: str) -> ItemInstance | None:
        return next((item for item in self.items if item.id == item_id), None)

    def _stacks_of(self, item_id: str) -> list[ItemInstance]:
        return [item for item in self.items if item.id == item_id]

    def _room_for(self, item: ItemInstance) -> int:
        free_slots = self.capacity - len(self.items)
        if not item.definition.stackable:
            return 1 if free_slots > 0 else 0
        in_stacks = sum(self.stack_max - s.count for s in self._stacks_of(item.id))
        return in_stacks + free_slots * self.stack_max
