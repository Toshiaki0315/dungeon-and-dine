"""エンティティの基底 dataclass。

pyxel を import しないこと。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.systems.status import StatusEffects
from game.systems.turn import ACTION_COST, NORMAL_SPEED
from game.world.direction import Direction
from game.world.floor import Floor


@dataclass
class Entity:
    x: int
    y: int
    facing: Direction = Direction.DOWN
    speed: int = NORMAL_SPEED
    energy: int = ACTION_COST  # 生成直後から行動できる
    statuses: StatusEffects = field(default_factory=StatusEffects)

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    def try_move(self, floor: Floor, direction: Direction) -> bool:
        """その方向を向いてから移動を試みる。移動できたら True を返す。"""
        self.facing = direction
        if not floor.can_move(self.x, self.y, direction):
            return False
        self.x += direction.dx
        self.y += direction.dy
        return True
