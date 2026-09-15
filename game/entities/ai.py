"""敵AI（chase / wander / erratic / ranged / ambush / flee）。仕様書 8.1。

pyxel を import しないこと。
"""

from __future__ import annotations

import heapq
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from game.data_loader import dataclass_from_dict
from game.entities.monster import (
    ABILITY_BREATH,
    AI_AMBUSH,
    AI_ERRATIC,
    AI_FLEE,
    AI_RANGED,
    AI_WANDER,
    MODE_CHASE,
    MODE_IDLE,
    MODE_WANDER,
    Ability,
    Monster,
)
from game.world.direction import Direction, chebyshev
from game.world.floor import Floor

Position = tuple[int, int]


@dataclass(frozen=True)
class AIParams:
    """敵AIのパラメータ。balance.json の "ai" で定義する。"""

    erratic_move_chance: int
    flee_hp_ratio: float
    path_max_nodes: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AIParams:
        return dataclass_from_dict(cls, data, "ai")


class AIContext(Protocol):
    """AI が行動するときに使う、ゲーム側の窓口。"""

    floor: Floor
    rng: random.Random

    @property
    def player_pos(self) -> Position: ...

    def can_see_player(self, monster: Monster) -> bool: ...

    def player_is_stealthy(self) -> bool: ...

    def is_free_for_monster(self, x: int, y: int) -> bool: ...

    def move_monster(self, monster: Monster, direction: Direction) -> None: ...

    def monster_attack(self, monster: Monster) -> None: ...

    def monster_breath(self, monster: Monster, ability: Ability) -> None: ...

    def reveal_monster(self, monster: Monster) -> None: ...


def take_turn(monster: Monster, ctx: AIContext, params: AIParams) -> None:
    """モンスターの1回分の行動を決めて実行する。"""
    ai = monster.definition.ai
    player = ctx.player_pos

    if ai == AI_AMBUSH and monster.disguised:
        # 宝箱に擬態し、隣接されるまで動かない
        if chebyshev(monster.pos, player) <= 1:
            ctx.reveal_monster(monster)
        return

    sees = ctx.can_see_player(monster)
    if sees and monster.mode == MODE_WANDER and ctx.player_is_stealthy():
        sees = False  # 忍び足: 徘徊中の敵は気づかない
    if sees:
        monster.target = player
        monster.mode = MODE_CHASE

    if ai == AI_ERRATIC and ctx.rng.randrange(100) < params.erratic_move_chance:
        _random_step(monster, ctx)
        return
    low_hp = monster.hp <= monster.max_hp * params.flee_hp_ratio
    if ai == AI_FLEE and sees and low_hp and _step_away(monster, ctx, player):
        return
    if ai == AI_RANGED and sees:
        if chebyshev(monster.pos, player) <= 1:
            if _step_away(monster, ctx, player):
                return
        else:
            breath = monster.ability(ABILITY_BREATH)
            if breath is not None and has_clear_line(ctx, monster.pos, player, breath.range):
                ctx.monster_breath(monster, breath)
                return

    if monster.target is None:
        if monster.mode == MODE_WANDER:
            _random_step(monster, ctx)
        return

    if can_melee(ctx.floor, monster.pos, player):
        ctx.monster_attack(monster)
        return
    if monster.pos == monster.target:
        # 最後に見た位置まで来たが見失った
        monster.target = None
        monster.mode = MODE_WANDER if ai in (AI_WANDER, AI_ERRATIC) else MODE_IDLE
        return
    step = find_next_step(
        ctx.floor, monster.pos, monster.target, ctx.is_free_for_monster, params.path_max_nodes
    )
    if step is not None:
        ctx.move_monster(monster, step)


def can_melee(floor: Floor, attacker: Position, target: Position) -> bool:
    """隣接していて、角に遮られていなければ攻撃できる。"""
    direction = Direction.toward(attacker, target)
    return (
        direction is not None
        and chebyshev(attacker, target) == 1
        and floor.can_move(*attacker, direction)
    )


def has_clear_line(ctx: AIContext, start: Position, goal: Position, max_range: int) -> bool:
    """縦・横・斜めの直線上 max_range マス以内で、途中に壁や敵がいないか。"""
    dx, dy = goal[0] - start[0], goal[1] - start[1]
    distance = chebyshev(start, goal)
    if distance == 0 or distance > max_range:
        return False
    if not (dx == 0 or dy == 0 or abs(dx) == abs(dy)):
        return False
    direction = Direction.toward(start, goal)
    assert direction is not None
    x, y = start
    for _ in range(distance):
        if not ctx.floor.can_move(x, y, direction):
            return False
        x, y = x + direction.dx, y + direction.dy
        if (x, y) != goal and not ctx.is_free_for_monster(x, y):
            return False
    return True


def find_next_step(
    floor: Floor,
    start: Position,
    goal: Position,
    is_free: Callable[[int, int], bool],
    max_nodes: int,
) -> Direction | None:
    """A* 法で goal へ向かう最初の1歩を返す（8方向・角抜け禁止）。

    goal のマスは塞がっていてもよい。探索が打ち切られたり道がなかったりしたときは、
    goal に最も近づけたマスへ向かう。
    """
    if start == goal:
        return None
    came_from: dict[Position, tuple[Position, Direction]] = {}
    cost = {start: 0}
    heap = [(chebyshev(start, goal), 0, start)]
    best = start
    expanded = 0
    while heap and expanded < max_nodes:
        _, g, current = heapq.heappop(heap)
        if current == goal:
            break
        if g > cost[current]:
            continue
        expanded += 1
        for direction in Direction:
            if not floor.can_move(*current, direction):
                continue
            nxt = (current[0] + direction.dx, current[1] + direction.dy)
            if nxt != goal and not is_free(*nxt):
                continue
            if g + 1 < cost.get(nxt, max_nodes * 10):
                cost[nxt] = g + 1
                came_from[nxt] = (current, direction)
                heapq.heappush(heap, (g + 1 + chebyshev(nxt, goal), g + 1, nxt))
                if chebyshev(nxt, goal) < chebyshev(best, goal):
                    best = nxt

    node = goal if goal in came_from else best
    if node == start:
        return None
    while True:
        previous, direction = came_from[node]
        if previous == start:
            return direction
        node = previous


def _movable_directions(monster: Monster, ctx: AIContext) -> list[Direction]:
    return [
        d
        for d in Direction
        if ctx.floor.can_move(monster.x, monster.y, d)
        and ctx.is_free_for_monster(monster.x + d.dx, monster.y + d.dy)
    ]


def _random_step(monster: Monster, ctx: AIContext) -> None:
    directions = _movable_directions(monster, ctx)
    if directions:
        ctx.move_monster(monster, ctx.rng.choice(directions))


def _step_away(monster: Monster, ctx: AIContext, threat: Position) -> bool:
    """threat から離れる方向へ1歩動く。離れられなければ False。"""
    current = chebyshev(monster.pos, threat)
    best: Direction | None = None
    best_distance = current
    for d in _movable_directions(monster, ctx):
        distance = chebyshev((monster.x + d.dx, monster.y + d.dy), threat)
        if distance > best_distance:
            best, best_distance = d, distance
    if best is None:
        return False
    ctx.move_monster(monster, best)
    return True
