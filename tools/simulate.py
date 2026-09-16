"""バランス調整用の自動プレイ。仕様書 15章（フェーズ7）。

ロジック層（game/systems/game_state.py）だけを使い、簡単な方針で B1F から潜って結果を集計する。
描画は行わないので、pyxel のウィンドウは開かない。ゲーム本体からは import しないこと。

    .venv/bin/python tools/simulate.py --runs 50
    .venv/bin/python tools/simulate.py --runs 5 --verbose
    .venv/bin/python tools/simulate.py --runs 20 --max-turns 5000 --seed 7
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from game import data_loader  # noqa: E402
from game.entities import ai  # noqa: E402
from game.entities.item import (  # noqa: E402
    CATEGORY_AMMO,
    CATEGORY_INGREDIENT,
    GOLD_ID,
    ItemInstance,
)
from game.systems import progression  # noqa: E402
from game.systems.game_state import (  # noqa: E402
    EquipResult,
    GameParams,
    GameState,
    MoveResult,
)
from game.systems.progression import exp_to_next_level  # noqa: E402
from game.systems.skills import SKILL_ATTACK  # noqa: E402
from game.world.direction import Direction, chebyshev  # noqa: E402

HEAL_THRESHOLD = 0.5  # 最大HPのこの割合を下回ったら回復する
HUNGRY_THRESHOLD = 40  # 満腹度がこれ以下なら食べる
COOK_THRESHOLD = 80  # 満腹度がこれ以下なら、焚き火のそばで作りだめする
FLEE_HP_RATIO = 0.3  # HP がこの割合を下回ったら戦わずに先を急ぐ
HUNT_RANGE = 8  # このマス数以内に見えている敵は倒しに行く
HUNT_HP_RATIO = 0.5  # HP がこの割合を下回ったら、敵を避けて先を急ぐ
LEVEL_PER_FLOOR = 1.2  # この階に対するレベルの目安。足りないうちは階段へ急がない


@dataclass
class RunResult:
    floor: int
    turn: int
    level: int
    cleared: bool
    starved: bool
    boss_level: int | None = None  # ボス階に着いたときのレベル（着かなければ None）

    @property
    def outcome(self) -> str:
        if self.cleared:
            return "クリア"
        return "飢餓" if self.starved else "戦闘"


class AutoPlayer:
    """簡単な方針で1回の挑戦を進める。"""

    def __init__(self, state: GameState) -> None:
        self.state = state

    def step(self) -> None:
        state = self.state
        if self._heal() or self._eat() or self._cook() or self._equip():
            return
        if self._rest_before_boss():
            return
        if self._can_fight() and self._shoot():
            return
        target = self._adjacent_monster()
        if target is not None and self._can_fight():
            direction = Direction.toward(state.player.pos, target)
            if direction is not None:
                state.face(direction)
                if not self._use_attack_skill():
                    state.attack()
                return
        if state.can_descend:
            state.descend()
            return
        self._walk_toward(self._goal())

    # --- 方針 ---

    def _heal(self) -> bool:
        p = self.state.player
        if p.hp > p.max_hp * HEAL_THRESHOLD:
            return False
        item = self._find_effect("heal")
        return item is not None and self.state.use_item(item)

    def _eat(self) -> bool:
        if self.state.player.satiety > HUNGRY_THRESHOLD:
            return False
        item = self._best_food()
        return item is not None and self.state.use_item(item)

    def _best_food(self) -> ItemInstance | None:
        """満腹度の回復量が大きいものから食べる（生の食材は毒の危険があるので後回し）。"""
        foods = [
            (effect.value, item.definition.category != CATEGORY_INGREDIENT, item)
            for item in self.state.inventory.items
            for effect in item.definition.effects
            if effect.type == "satiety" and effect.value > 0
        ]
        if not foods:
            return None
        return max(foods, key=lambda f: (f[1], f[0]))[2]

    def _shoot(self) -> bool:
        """弓と矢があれば、正面の直線上の敵を撃つ。"""
        state = self.state
        weapon = state.effective_weapon()
        if not weapon.uses_arrows:
            return False
        p = state.player
        for monster in state.visible_monsters():
            if monster.disguised:
                continue
            direction = Direction.toward(p.pos, monster.pos)
            if direction is None or not ai.has_clear_line(state, p.pos, monster.pos, weapon.length):
                continue
            state.face(direction)
            state.attack()
            return True
        return False

    def _use_attack_skill(self) -> bool:
        """MP に余裕があれば、いちばん強い攻撃スキルを使う。"""
        state = self.state
        p = state.player
        skills = [
            skill
            for skill in state.learned_skills()
            if skill.type == SKILL_ATTACK
            and p.mp >= skill.mp
            # 反動で倒れそうなときは「捨て身の一撃」を使わない
            and p.hp > p.max_hp * skill.self_damage_ratio * 2
        ]
        if not skills:
            return False
        best = max(skills, key=lambda s: s.multiplier)
        if best.multiplier <= 1.0:
            return False
        return state.use_skill(best.id)

    def _cook(self) -> bool:
        """焚き火のそばか携帯コンロがあり、食材が2つ以上あれば料理する。"""
        state = self.state
        if state.player.satiety > COOK_THRESHOLD or state.heat_source() is None:
            return False
        materials = self._ingredients()[:2]
        if len(materials) < 2:
            return False
        plan = state.plan_cooking(materials)
        return plan is not None and state.apply_cooking(plan)

    def _equip(self) -> bool:
        """より強い装備に持ち替える（空いている部位にはそのまま着ける）。"""
        state = self.state
        for item in state.inventory.items:
            slot = item.definition.slot
            if slot is None or state.player.is_equipped(item):
                continue
            current = state.player.equipment[slot]
            if current is not None and self._power(item) <= self._power(current):
                continue
            if current is not None and current.cursed:
                continue  # 呪われていて外せない
            return state.equip(item, confirmed=True) != EquipResult.FAILED
        return False

    @staticmethod
    def _power(item: ItemInstance) -> int:
        """装備の強さの目安（未鑑定でも、種類の基本値で比べる）。"""
        weapon, armor = item.definition.weapon, item.definition.armor
        base = weapon.attack if weapon is not None else (armor.defense if armor else 0)
        return base + (item.modifier if item.identified else 0)

    def _find_effect(self, effect_type: str) -> ItemInstance | None:
        return next(
            (
                item
                for item in self.state.inventory.items
                if any(e.type == effect_type for e in item.definition.effects)
                and item.definition.category != CATEGORY_AMMO
            ),
            None,
        )

    def _adjacent_monster(self) -> tuple[int, int] | None:
        player = self.state.player.pos
        for monster in self.state.floor.monsters:
            if not monster.disguised and chebyshev(monster.pos, player) == 1:
                return monster.pos
        return None

    def _needs_levels(self) -> bool:
        """この階層に対してレベルが足りているか（足りなければ敵を探して倒す）。"""
        state = self.state
        return state.player.level < state.floor.number * LEVEL_PER_FLOOR

    def _goal(self) -> tuple[int, int]:
        """目的地。ボス階ではボス、それ以外では下り階段へ向かう。"""
        state = self.state
        if state.is_boss_floor:
            p = state.player
            hurt = p.hp < p.max_hp or p.mp < p.max_mp
            can_recover = p.satiety > 0 or self._best_food() is not None
            if hurt and state.floor.campfires and can_recover:
                return state.floor.campfires[0].pos  # 全快するまで焚き火で休む
            if state.floor.monsters:
                return state.floor.monsters[0].pos
        if self._is_hungry():
            campfire = self._cookable_campfire()
            if campfire is not None:
                return campfire  # 焚き火まで行って料理する
            return state.floor.stairs  # 空腹のときは寄り道しない

        prey = self._nearest_monster()
        if prey is not None:
            return prey  # 経験値を稼ぐため、近くの敵は倒しに行く
        floor_item = next((i for i in state.floor.items if i.item.id != GOLD_ID), None)
        if floor_item is not None and chebyshev(floor_item.pos, state.player.pos) <= 6:
            return floor_item.pos  # 近くに落ちていれば拾う
        return state.floor.stairs

    def _rest_before_boss(self) -> bool:
        """ボス階では、焚き火のそば（敵が入れない安全地帯）で回復してから挑む。"""
        state = self.state
        p = state.player
        if not state.is_boss_floor or not state.floor.in_safe_zone(*p.pos):
            return False
        if p.hp >= p.max_hp and p.mp >= p.max_mp:
            return False
        if self._best_food() is not None and p.satiety <= COOK_THRESHOLD:
            return False  # 食べられるうちは食べて、満腹度を保ちながら回復する
        if p.satiety <= 0:
            return False  # 満腹度が尽きたら、待っていても減るだけ
        state.wait()
        return True

    def _can_fight(self) -> bool:
        p = self.state.player
        return p.hp >= p.max_hp * FLEE_HP_RATIO

    def _is_hungry(self) -> bool:
        return self.state.player.satiety <= HUNGRY_THRESHOLD * 2

    def _ingredients(self) -> list[ItemInstance]:
        return [
            item
            for item in self.state.cooking_candidates()
            if item.definition.category == CATEGORY_INGREDIENT
        ]

    def _cookable_campfire(self) -> tuple[int, int] | None:
        """料理できる材料を持っているときだけ、この階の焚き火の位置を返す。"""
        state = self.state
        if len(self._ingredients()) < 2 or not state.floor.campfires:
            return None
        return min(
            (c.pos for c in state.floor.campfires),
            key=lambda pos: chebyshev(pos, state.player.pos),
        )

    def _nearest_monster(self) -> tuple[int, int] | None:
        state = self.state
        p = state.player
        if p.hp < p.max_hp * HUNT_HP_RATIO:
            return None  # 弱っているときは深追いしない
        seen = [
            m.pos
            for m in state.visible_monsters()
            if not m.disguised and chebyshev(m.pos, p.pos) <= HUNT_RANGE
        ]
        return min(seen, key=lambda pos: chebyshev(pos, p.pos), default=None)

    def _walk_toward(self, goal: tuple[int, int]) -> None:
        state = self.state
        step = ai.find_next_step(
            state.floor,
            state.player.pos,
            goal,
            lambda x, y: state.floor.is_walkable(x, y) and state.floor.chest_at(x, y) is None,
            state.params.ai.path_max_nodes,
        )
        if step is None:
            state.wait()
            return
        if state.move_player(step, confirm_trap=True) == MoveResult.BLOCKED:
            state.wait()


# 終盤の確認で持たせる装備と道具（そこまで潜った人が持っていそうな一式）
LATE_GEAR = ("katana", "iron_shield", "iron_helm", "chain_mail", "leather_boots")
LATE_ITEMS = (("herb", 5), ("ration", 3), ("mana_herb", 2))


def prepare(state: GameState, floor: int, level: int) -> None:
    """途中の階・レベルから始める（終盤とボス戦の確認用）。"""
    while state.player.level < level:
        needed = exp_to_next_level(state.player.level, state.params.progression)
        progression.gain_exp(state.player, needed, state.params.progression, state.catalog.skills)
    if level > 1:
        for item_id in LATE_GEAR:
            item = ItemInstance(state.catalog.items[item_id])
            state.inventory.add(item)
            state.equip(item, confirmed=True)
        for item_id, count in LATE_ITEMS:
            for _ in range(count):
                state.inventory.add(ItemInstance(state.catalog.items[item_id]))
    state.player.hp, state.player.mp = state.player.max_hp, state.player.max_mp
    if floor > 1:
        state.enter_floor(floor)
    state.scheduler.turn = 0


def simulate_run(
    seed: int,
    params: GameParams,
    max_turns: int,
    verbose: bool,
    start_floor: int = 1,
    start_level: int = 1,
) -> RunResult:
    state = GameState(seed, params)
    prepare(state, start_floor, start_level)
    player = AutoPlayer(state)
    boss_level: int | None = None
    while not state.run_over and state.turn < max_turns:
        before = state.floor.number
        player.step()
        if params.is_boss_floor(state.floor.number) and boss_level is None:
            boss_level = state.player.level
        if verbose and state.floor.number != before:
            p = state.player
            print(f"  B{state.floor.number}F  {state.turn}ターン  Lv{p.level}  HP{p.hp}/{p.max_hp}")
    return RunResult(
        floor=state.floor.number,
        turn=state.turn,
        level=state.player.level,
        cleared=state.cleared,
        starved=state.player.satiety == 0 and state.is_game_over,
        boss_level=boss_level,
    )


def report(results: list[RunResult]) -> None:
    runs = len(results)
    floors = sorted(r.floor for r in results)
    print(f"\n{runs}回の挑戦")
    print(f"  到達階: 平均 B{sum(floors) / runs:.1f}F  最深 B{floors[-1]}F  最浅 B{floors[0]}F")
    print(f"  ターン: 平均 {sum(r.turn for r in results) / runs:.0f}")
    print(f"  レベル: 平均 {sum(r.level for r in results) / runs:.1f}")
    outcomes = Counter(r.outcome for r in results)
    for outcome, count in outcomes.most_common():
        print(f"  {outcome}: {count}回（{count / runs:.0%}）")

    reached = [r.boss_level for r in results if r.boss_level is not None]
    if reached:
        average = sum(reached) / len(reached)
        print(f"  ボス階へ到達: {len(reached)}回  そのときの平均 Lv{average:.1f}")

    print("\n  階層ごとの終了数")
    per_floor = Counter(r.floor for r in results)
    for floor in sorted(per_floor):
        bar = "#" * per_floor[floor]
        print(f"   B{floor:>2}F  {per_floor[floor]:>3}  {bar}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="自動プレイでバランスを確認する")
    parser.add_argument("--runs", type=int, default=20, help="試行回数（既定: 20）")
    parser.add_argument("--seed", type=int, default=None, help="乱数シード（省略時はランダム）")
    parser.add_argument("--max-turns", type=int, default=20000, help="1回の上限ターン数")
    parser.add_argument("--verbose", action="store_true", help="階を移るたびに状況を表示する")
    parser.add_argument(
        "--start-floor", type=int, default=1, help="この階から始める（終盤の確認用）"
    )
    parser.add_argument("--start-level", type=int, default=1, help="このレベルから始める（同上）")
    args = parser.parse_args(argv)

    params = GameParams.from_data(data_loader.load_all())
    seeds = random.Random(args.seed).sample(range(10**9), args.runs)
    results: list[RunResult] = []
    for index, seed in enumerate(seeds, start=1):
        if args.verbose:
            print(f"[{index}/{args.runs}] シード {seed}")
        result = simulate_run(
            seed, params, args.max_turns, args.verbose, args.start_floor, args.start_level
        )
        results.append(result)
        if args.verbose:
            print(f"  → {result.outcome}  B{result.floor}F  {result.turn}ターン")
    report(results)


if __name__ == "__main__":
    main()
