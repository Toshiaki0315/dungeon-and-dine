"""1回の挑戦（ラン）中のゲーム状態と、プレイヤーの行動によるターン進行。

描画や入力から切り離し、テストから直接操作できるようにしている。
pyxel を import しないこと。
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Any

from game import rng as rng_module
from game.entities import ai
from game.entities.ai import AIParams
from game.entities.item import CATEGORY_AMMO, GOLD_ID, Effect, FloorItem, ItemInstance, WeaponStats
from game.entities.monster import ABILITY_ON_HIT_STATUS, MODE_CHASE, Ability, Monster
from game.entities.player import Player, PlayerParams
from game.systems import progression, spawn
from game.systems.catalog import Catalog
from game.systems.combat import REACH_LINE, CombatParams, CombatStats, reach_cells, roll_attack
from game.systems.inventory import Inventory
from game.systems.message_log import MessageLog, highlight
from game.systems.progression import ProgressionParams, SurvivalParams
from game.systems.skills import SKILL_ATTACK, SKILL_STEALTH, SkillDef, skills_up_to_level
from game.systems.spawn import SpawnParams
from game.systems.status import AILMENT, speed_for, try_inflict
from game.systems.traps import (
    TRAP_ALARM,
    TRAP_DAMAGE_STATUS,
    TRAP_PIT,
    TRAP_RUST,
    TRAP_SATIETY,
    TRAP_STATUS,
    TRAP_WARP,
    Trap,
    TrapParams,
    search_around,
)
from game.systems.turn import TurnScheduler
from game.world.direction import Direction, chebyshev
from game.world.floor import Area, Floor, area_for_floor
from game.world.fov import FogMap, FovParams, Visibility, compute_visible
from game.world.mapgen import MapGenParams, generate_floor
from game.world.tiles import Tile

Position = tuple[int, int]

# フェーズ3で使える消費アイテムの効果（それ以外は「未実装」と表示して使わない）
IMPLEMENTED_EFFECTS = frozenset({"heal", "restore_mp", "cure", "satiety", "fire_blast"})

# 状態異常にかかったときのログ（ない場合は「〇〇状態になった」）
INFLICT_MESSAGES: dict[str, str] = {
    "poison": "毒を受けた！",
    "confusion": "混乱した！",
    "sleep": "眠ってしまった！",
    "slow": "動きが鈍くなった！",
    "blind": "目が見えなくなった！",
    "max_hp_down": "最大HPが下がった！",
    "mana_drain": "魔力を吸われている！",
}


@dataclass(frozen=True)
class GameParams:
    """data/ から読み込んだ、ラン全体で使うパラメータ。"""

    catalog: Catalog
    mapgen: MapGenParams
    player: PlayerParams
    survival: SurvivalParams
    progression: ProgressionParams
    combat: CombatParams
    spawn: SpawnParams
    ai: AIParams
    traps: TrapParams
    fov: FovParams
    inventory_capacity: int
    inventory_stack_max: int
    areas: tuple[Area, ...]

    @classmethod
    def from_data(cls, data: Mapping[str, Mapping[str, Any]]) -> GameParams:
        balance = data["balance"]
        return cls(
            catalog=Catalog.from_data(data),
            mapgen=MapGenParams.from_dict(balance["mapgen"]),
            player=PlayerParams.from_dict(balance["player"]),
            survival=SurvivalParams.from_dict(balance["survival"]),
            progression=ProgressionParams.from_dict(balance["progression"]),
            combat=CombatParams.from_dict(balance["combat"]),
            spawn=SpawnParams.from_dict(balance["spawn"]),
            ai=AIParams.from_dict(balance["ai"]),
            traps=TrapParams.from_dict(balance["traps"]),
            fov=FovParams.from_dict(balance["fov"]),
            inventory_capacity=int(balance["inventory"]["capacity"]),
            inventory_stack_max=int(balance["inventory"]["stack_max"]),
            areas=tuple(Area.from_dict(area) for area in data["floors"]["areas"]),
        )

    @property
    def last_floor(self) -> int:
        return max(area.last_floor for area in self.areas)


class MoveResult(Enum):
    MOVED = auto()
    ATTACKED = auto()  # 移動先に敵がいたので攻撃した
    BLOCKED = auto()  # 壁などで進めなかった（向きだけ変わる）
    CONFIRM_TRAP = auto()  # 発見済みの罠があるので、確認してから進む


class GameState:
    def __init__(self, run_seed: int, params: GameParams) -> None:
        self.run_seed = run_seed
        self.params = params
        self.catalog = params.catalog
        self.rng = random.Random(run_seed)  # 戦闘や敵AIなど、プレイ中に使う乱数
        self.player = Player.from_params(params.player)
        self.player.skills = skills_up_to_level(self.player.level, self.catalog.skills)
        self.inventory = Inventory(params.inventory_capacity, params.inventory_stack_max)
        self.scheduler = TurnScheduler()
        self.log = MessageLog()
        self.interrupted = False  # 連続移動を止めるべき出来事（敵の発見・被ダメージなど）
        self._next_uid_value = 0
        self._visible_monster_ids: set[int] = set()
        self._sight: set[Position] = set()  # 敵がプレイヤーに気づける範囲（盲目の影響を受けない）
        self._death_logged = False
        self.floor: Floor
        self.area: Area
        self.fog: FogMap
        self.enter_floor(1)
        self.log.add(f"{self.player.name}は迷宮の奥へ足を踏み入れた。")

    # --- 状態の参照 ---

    @property
    def turn(self) -> int:
        return self.scheduler.turn

    @property
    def is_game_over(self) -> bool:
        return self.player.hp <= 0

    @property
    def player_pos(self) -> Position:
        return self.player.pos

    @property
    def player_on_stairs(self) -> bool:
        return self.floor.tile_at(*self.player.pos) == Tile.STAIRS_DOWN

    @property
    def can_descend(self) -> bool:
        # B20F（ボス階）はフェーズ7で固定レイアウトにし、階段を置かない
        return self.player_on_stairs and self.floor.number < self.params.last_floor

    @property
    def can_cook(self) -> bool:
        # 焚き火と携帯コンロはフェーズ5で実装する
        return False

    def visible_monsters(self) -> list[Monster]:
        return [m for m in self.floor.monsters if self.fog.state(*m.pos) == Visibility.VISIBLE]

    def learned_skills(self) -> list[SkillDef]:
        return [self.catalog.skills[skill_id] for skill_id in self.player.skills]

    def player_status_names(self) -> list[str]:
        return [self.catalog.statuses[s].name for s in self.player.statuses.active_ids()]

    def consume_interrupt(self) -> bool:
        """連続移動を止めるべき出来事があったかを返し、フラグを下ろす。"""
        interrupted = self.interrupted
        self.interrupted = False
        return interrupted

    def player_combat_stats(self) -> CombatStats:
        p = self.player
        weapon = self.effective_weapon()
        statuses = self.catalog.statuses
        atk_bonus = statuses["atk_up"].value if "atk_up" in p.statuses else 0
        def_bonus = statuses["def_up"].value if "def_up" in p.statuses else 0
        crit_rate = (
            weapon.crit_rate if weapon.crit_rate is not None else self.params.combat.crit_rate
        )
        return CombatStats(
            atk=p.atk + weapon.attack + atk_bonus,
            defense=p.defense + def_bonus,
            hit=p.hit,
            evade=p.evade,
            crit_rate=crit_rate,
        )

    def effective_weapon(self) -> WeaponStats:
        """装備中の武器の性能。武器がないとき・矢のない弓は素手として扱う。"""
        item = self.player.weapon
        weapon = item.definition.weapon if item is not None else None
        if weapon is None or (weapon.uses_arrows and self._arrows() is None):
            return self.catalog.unarmed
        return weapon

    # --- 階層 ---

    def enter_floor(self, number: int) -> None:
        floor_rng = rng_module.floor_rng(self.run_seed, number)
        self.floor = generate_floor(floor_rng, number, self.params.mapgen)
        spawn.populate_floor(self.floor, floor_rng, self.catalog, self.params.spawn, self._next_uid)
        self.area = area_for_floor(self.params.areas, number)
        self.fog = FogMap(self.floor.width, self.floor.height)
        self.player.x, self.player.y = self.floor.start
        self._visible_monster_ids = set()
        self.update_fov()

    def update_fov(self) -> None:
        p = self.player
        fov = self.params.fov
        if "sight_up" in p.statuses:
            extra = self.catalog.statuses["sight_up"].value
            fov = replace(fov, corridor_adjacent=fov.corridor_adjacent + extra)
        sight = compute_visible(self.floor, p.x, p.y, p.facing, fov)
        blind = "blind" in p.statuses
        self.fog.update(
            compute_visible(self.floor, p.x, p.y, p.facing, fov, blind=True) if blind else sight
        )
        self._sight = sight

        visible_ids = {m.uid for m in self.visible_monsters() if not m.disguised}
        if visible_ids - self._visible_monster_ids:
            self.interrupted = True
        self._visible_monster_ids = visible_ids

    # --- プレイヤーの行動（ターンを消費する） ---

    def move_player(self, direction: Direction, *, confirm_trap: bool = False) -> MoveResult:
        """1歩進む。移動先に敵がいれば攻撃する。壁に向かった場合は向きだけ変わる。"""
        if self.is_game_over:
            return MoveResult.BLOCKED
        p = self.player
        if "confusion" in p.statuses:
            direction = self.rng.choice(list(Direction))
            confirm_trap = True  # 混乱中は罠に気をつけられない

        if not self.floor.can_move(p.x, p.y, direction):
            p.facing = direction
            self.update_fov()
            return MoveResult.BLOCKED
        target = (p.x + direction.dx, p.y + direction.dy)
        if self.floor.monster_at(*target) is not None:
            p.facing = direction
            self._attack_forward()
            return MoveResult.ATTACKED
        trap = self.floor.trap_at(*target)
        if trap is not None and trap.discovered and not confirm_trap:
            p.facing = direction
            return MoveResult.CONFIRM_TRAP

        p.try_move(self.floor, direction)
        self.update_fov()
        self._after_player_moved()
        self._end_player_action()
        return MoveResult.MOVED

    def face(self, direction: Direction) -> None:
        """向きだけを変える（ターンは進まない）。"""
        self.player.facing = direction
        self.update_fov()

    def attack(self) -> None:
        """向いている方向へ、装備中の武器の範囲で通常攻撃する。"""
        if self.is_game_over:
            return
        if "confusion" in self.player.statuses:
            self.player.facing = self.rng.choice(list(Direction))
        self._attack_forward()

    def wait(self) -> None:
        """足踏みして1ターン経過させ、周囲の罠を探す。"""
        if self.is_game_over:
            return
        p = self.player
        for trap in search_around(self.floor, p.x, p.y, self.rng, self.params.traps.search_chance):
            self.log.add(f"{highlight(trap.name)}を見つけた。")
            self.interrupted = True
        self._end_player_action()

    def use_skill(self, skill_id: str) -> bool:
        """スキルを使う。使えなかったとき（MP不足など）はターンを消費せず False を返す。"""
        p = self.player
        if self.is_game_over or skill_id not in p.skills:
            return False
        skill = self.catalog.skills[skill_id]
        if skill.type not in (SKILL_ATTACK, SKILL_STEALTH):
            self.log.add(f"「{skill.name}」は未実装です。")
            return False
        if p.mp < skill.mp:
            self.log.add("MPが足りない。")
            return False

        p.mp -= skill.mp
        self.log.add(f"{p.name}は「{skill.name}」を使った！")
        if skill.type == SKILL_ATTACK:
            if "confusion" in p.statuses:
                p.facing = self.rng.choice(list(Direction))
            cells = reach_cells(self.floor, p.x, p.y, p.facing, skill.area or "front")
            targets = self._monsters_in(cells, first_only=False)
            if not targets:
                self.log.add("しかし、そこには何もいなかった。")
            for monster in targets:
                self._player_hits(monster, multiplier=skill.multiplier)
            if skill.self_damage_ratio > 0:
                recoil = max(1, math.floor(p.max_hp * skill.self_damage_ratio))
                self.log.add(f"{p.name}は反動で{recoil}のダメージを受けた。")
                self._damage_player(recoil)
        else:
            p.statuses.add(self.catalog.statuses["stealth"], skill.duration)
        self._end_player_action()
        return True

    def use_item(self, item: ItemInstance) -> bool:
        """アイテムを使う（食べる・読む）。使えなかったときは False を返す。"""
        definition = item.definition
        if self.is_game_over or item not in self.inventory.items:
            return False
        label = definition.use_label
        if label is None:
            self.log.add(f"{highlight(definition.name)}は使えない。")
            return False
        if any(effect.type not in IMPLEMENTED_EFFECTS for effect in definition.effects):
            self.log.add(f"{highlight(definition.name)}はまだ使えない（未実装）。")
            return False

        self.inventory.take_one(item)
        verb = {"食べる": "食べた", "読む": "読んだ"}.get(label, "使った")
        self.log.add(f"{self.player.name}は{highlight(definition.name)}を{verb}。")
        for effect in definition.effects:
            self._apply_item_effect(effect)
        self._end_player_action()
        return True

    def throw_item(self, item: ItemInstance) -> bool:
        """向いている方向の直線上に投げる。最初に当たった敵にダメージを与える。"""
        if self.is_game_over or item not in self.inventory.items:
            return False
        p = self.player
        thrown = self.inventory.take_one(item)
        if "confusion" in p.statuses:
            p.facing = self.rng.choice(list(Direction))
        self.log.add(f"{p.name}は{highlight(thrown.definition.name)}を投げた。")

        landing = p.pos
        cells = reach_cells(
            self.floor, p.x, p.y, p.facing, REACH_LINE, self.params.combat.throw_range
        )
        for cell in cells:
            monster = self.floor.monster_at(*cell)
            if monster is not None:
                self._reveal_if_disguised(monster)
                self._damage_monster(monster, self.params.combat.throw_damage)
                break
            landing = cell
        else:
            if not self._drop_to_floor(thrown, landing):
                self.log.add(f"{highlight(thrown.definition.name)}はどこかへ消えてしまった。")
        self._end_player_action()
        return True

    def drop_item(self, item: ItemInstance) -> bool:
        """足元に置く。すでに何か置いてあるときや階段の上には置けない。"""
        if self.is_game_over or item not in self.inventory.items:
            return False
        p = self.player
        if self.floor.item_at(*p.pos) is not None or self.player_on_stairs:
            self.log.add("ここには置けない。")
            return False
        self.inventory.remove(item)
        self.floor.items.append(FloorItem(item, *p.pos))
        self.log.add(f"{highlight(item.name)}を足元に置いた。")
        self._end_player_action()
        return True

    def descend(self) -> bool:
        """下り階段の上にいれば次の階へ進む（ターンは進まない）。"""
        if not self.can_descend:
            return False
        self._go_down()
        self.log.add(f"{self.player.name}は B{self.floor.number}F へ降りた。")
        return True

    # --- AIContext（entities/ai.py から呼ばれる） ---

    def can_see_player(self, monster: Monster) -> bool:
        return monster.pos in self._sight

    def player_is_stealthy(self) -> bool:
        return "stealth" in self.player.statuses

    def is_free_for_monster(self, x: int, y: int) -> bool:
        return (
            self.floor.is_walkable(x, y)
            and self.floor.monster_at(x, y) is None
            and (x, y) != self.player.pos
        )

    def move_monster(self, monster: Monster, direction: Direction) -> None:
        nx, ny = monster.x + direction.dx, monster.y + direction.dy
        if self.is_free_for_monster(nx, ny):
            monster.try_move(self.floor, direction)

    def monster_attack(self, monster: Monster) -> None:
        p = self.player
        result = roll_attack(
            monster.combat_stats(self.params.combat.crit_rate),
            self.player_combat_stats(),
            self.rng,
            self.params.combat,
        )
        if not result.hit:
            self.log.add(f"{monster.name}の攻撃をかわした。")
            return
        self.log.add(f"{monster.name}の攻撃！ {p.name}は{result.damage}のダメージを受けた。")
        self._damage_player(result.damage)
        if self.is_game_over:
            return
        self._wake_player()
        for ability in monster.definition.abilities:
            if ability.type == ABILITY_ON_HIT_STATUS and ability.status is not None:
                self._inflict_player(ability.status, ability.chance)

    def monster_breath(self, monster: Monster, ability: Ability) -> None:
        p = self.player
        self.log.add(f"{monster.name}は炎を吐いた！")
        halve = ability.element == "fire" and "fire_resist" in p.statuses
        result = roll_attack(
            monster.combat_stats(self.params.combat.crit_rate),
            self.player_combat_stats(),
            self.rng,
            self.params.combat,
            halve=halve,
        )
        if not result.hit:
            self.log.add("しかし、炎はそれた。")
            return
        self.log.add(f"{p.name}は{result.damage}のダメージを受けた。")
        self._damage_player(result.damage)
        if not self.is_game_over:
            self._wake_player()

    def reveal_monster(self, monster: Monster) -> None:
        self._reveal_if_disguised(monster)

    # --- 内部処理: 攻撃 ---

    def _attack_forward(self) -> None:
        p = self.player
        weapon = self.effective_weapon()
        cells = reach_cells(self.floor, p.x, p.y, p.facing, weapon.reach, weapon.length)
        targets = self._monsters_in(cells, first_only=weapon.reach == REACH_LINE)
        if weapon.uses_arrows:
            arrows = self._arrows()
            assert arrows is not None
            self.inventory.take_one(arrows)
            self.log.add(f"{p.name}は矢を放った。")
        if not targets and not (
            weapon.pull_item_range > 0 and self._pull_item(weapon.pull_item_range)
        ):
            self.log.add(f"{p.name}の攻撃は空を切った。")
        for monster in targets:
            self._player_hits(monster)
        self._end_player_action()

    def _monsters_in(self, cells: list[Position], *, first_only: bool) -> list[Monster]:
        targets: list[Monster] = []
        for cell in cells:
            monster = self.floor.monster_at(*cell)
            if monster is not None:
                targets.append(monster)
                if first_only:
                    break
        return targets

    def _player_hits(self, monster: Monster, multiplier: float = 1.0) -> None:
        self._reveal_if_disguised(monster)
        result = roll_attack(
            self.player_combat_stats(),
            monster.combat_stats(self.params.combat.crit_rate),
            self.rng,
            self.params.combat,
            multiplier=multiplier,
        )
        if not result.hit:
            self.log.add(f"{self.player.name}の攻撃は{monster.name}に当たらなかった。")
            self._alert(monster)
            return
        self._damage_monster(monster, result.damage, critical=result.critical)

    def _damage_monster(self, monster: Monster, damage: int, *, critical: bool = False) -> None:
        monster.hp -= damage
        prefix = "会心の一撃！ " if critical else ""
        self.log.add(f"{prefix}{monster.name}に{damage}のダメージ。")
        if monster.hp <= 0:
            self._kill_monster(monster)
        else:
            self._alert(monster)

    def _alert(self, monster: Monster) -> None:
        """攻撃された敵はプレイヤーに気づく。"""
        monster.mode = MODE_CHASE
        monster.target = self.player.pos

    def _kill_monster(self, monster: Monster) -> None:
        if monster in self.floor.monsters:
            self.floor.monsters.remove(monster)
        exp = monster.definition.exp
        self.log.add(f"{monster.name}を倒した！ {exp}の経験値を得た。")
        for message in progression.gain_exp(
            self.player, exp, self.params.progression, self.catalog.skills
        ):
            self.log.add(message)
        # 食材のドロップはフェーズ5で実装する
        if self.rng.randrange(100) < self.params.spawn.monster_gold_drop_chance:
            amount = spawn.gold_amount(self.rng, self.floor.number, self.params.spawn)
            self._drop_to_floor(ItemInstance(self.catalog.items[GOLD_ID], amount), monster.pos)

    def _reveal_if_disguised(self, monster: Monster) -> None:
        if not monster.disguised:
            return
        monster.disguised = False
        self._alert(monster)
        self.log.add(f"{highlight('宝箱')}は{monster.name}だった！")
        self.interrupted = True

    # --- 内部処理: アイテム ---

    def _arrows(self) -> ItemInstance | None:
        return next(
            (i for i in self.inventory.items if i.definition.category == CATEGORY_AMMO), None
        )

    def _apply_item_effect(self, effect: Effect) -> None:
        p = self.player
        if effect.type == "heal":
            before = p.hp
            p.hp = min(p.max_hp, p.hp + effect.value)
            self.log.add(f"HPが{p.hp - before}回復した。")
        elif effect.type == "restore_mp":
            before = p.mp
            p.mp = min(p.max_mp, p.mp + effect.value)
            self.log.add(f"MPが{p.mp - before}回復した。")
        elif effect.type == "cure":
            cured = [self.catalog.statuses[s].name for s in effect.statuses if p.statuses.remove(s)]
            self.log.add(f"{'・'.join(cured)}が治った。" if cured else "何も起こらなかった。")
            p.speed = speed_for(p.statuses, self.catalog.statuses)
        elif effect.type == "satiety":
            p.satiety = min(p.max_satiety, p.satiety + effect.value)
            self.log.add("おなかがふくれた。")
        elif effect.type == "fire_blast":
            self.log.add("炎が巻き起こった！")
            for monster in list(self.floor.monsters):
                if chebyshev(monster.pos, p.pos) <= effect.radius:
                    self._reveal_if_disguised(monster)
                    self._damage_monster(monster, effect.value)

    def _pick_up_at_feet(self) -> None:
        p = self.player
        floor_item = self.floor.item_at(*p.pos)
        if floor_item is None:
            return
        item = floor_item.item
        name = item.name
        if item.id == GOLD_ID:
            p.gold += item.count
            self.floor.items.remove(floor_item)
            self.log.add(f"{item.count}Gを拾った。")
        elif self.inventory.add(item):
            self.floor.items.remove(floor_item)
            self.log.add(f"{highlight(name)}を拾った。")
        else:
            self.log.add(f"持ちきれない。{highlight(name)}を拾えなかった。")

    def _pull_item(self, max_range: int) -> bool:
        """ムチ: 正面の直線上の最も近いアイテムを足元に引き寄せる。"""
        p = self.player
        if self.floor.item_at(*p.pos) is not None:
            return False
        for cell in reach_cells(self.floor, p.x, p.y, p.facing, REACH_LINE, max_range):
            floor_item = self.floor.item_at(*cell)
            if floor_item is not None:
                floor_item.x, floor_item.y = p.pos
                self.log.add(f"{highlight(floor_item.item.name)}を引き寄せた。")
                self._pick_up_at_feet()
                return True
        return False

    def _drop_to_floor(self, item: ItemInstance, pos: Position) -> bool:
        """pos か、その近くの空いている床にアイテムを置く。置けなければ False。"""
        for radius in range(3):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    cell = (pos[0] + dx, pos[1] + dy)
                    if chebyshev(cell, pos) == radius and self._can_place_item(cell):
                        self.floor.items.append(FloorItem(item, *cell))
                        return True
        return False

    def _can_place_item(self, cell: Position) -> bool:
        return (
            self.floor.tile_at(*cell) in (Tile.FLOOR, Tile.CORRIDOR)
            and self.floor.item_at(*cell) is None
            and self.floor.trap_at(*cell) is None
        )

    # --- 内部処理: 罠・状態異常 ---

    def _after_player_moved(self) -> None:
        floor = self.floor
        trap = floor.trap_at(*self.player.pos)
        if trap is not None:
            self._trigger_trap(trap)
        if self.floor is floor and not self.is_game_over:
            self._pick_up_at_feet()

    def _trigger_trap(self, trap: Trap) -> None:
        p = self.player
        definition = trap.definition
        trap.discovered = True
        self.interrupted = True
        self.log.add(f"{highlight(trap.name)}を踏んだ！")

        if definition.effect == TRAP_PIT:
            self.log.add(f"{p.name}は{definition.damage}のダメージを受けた。")
            self._damage_player(definition.damage)
            if not self.is_game_over and self.floor.number < self.params.last_floor:
                self._go_down()
                self.log.add(f"{p.name}は B{self.floor.number}F へ落ちてしまった。")
        elif definition.effect == TRAP_DAMAGE_STATUS:
            self.log.add(f"{p.name}は{definition.damage}のダメージを受けた。")
            self._damage_player(definition.damage)
            if not self.is_game_over and definition.status is not None:
                self._inflict_player(definition.status)
        elif definition.effect == TRAP_STATUS and definition.status is not None:
            self._inflict_player(definition.status)
        elif definition.effect == TRAP_WARP:
            cells = [
                (x, y)
                for y in range(self.floor.height)
                for x in range(self.floor.width)
                if self.is_free_for_monster(x, y) and self.floor.trap_at(x, y) is None
            ]
            if cells:
                p.x, p.y = self.rng.choice(cells)
                self.log.add(f"{p.name}はどこかへ飛ばされた。")
                self.update_fov()
        elif definition.effect == TRAP_SATIETY:
            p.satiety = max(0, p.satiety + definition.value)
            self.log.add("急におなかが減った。")
        elif definition.effect == TRAP_RUST:
            # 装備の修正値はフェーズ4で実装する
            self.log.add("しかし、錆びるものを身につけていなかった。")
        elif definition.effect == TRAP_ALARM:
            self.log.add("けたたましい音が鳴り響いた！")
            for monster in self.floor.monsters:
                self._alert(monster)

    def _inflict_player(self, status_id: str, chance: int = 100) -> bool:
        p = self.player
        definition = self.catalog.statuses[status_id]
        if not try_inflict(p.statuses, definition, self.rng, chance):
            return False
        if status_id == "max_hp_down":
            p.max_hp = max(1, p.max_hp - definition.value)
            p.hp = min(p.hp, p.max_hp)
        p.speed = speed_for(p.statuses, self.catalog.statuses)
        message = INFLICT_MESSAGES.get(status_id, f"{definition.name}状態になった！")
        self.log.add(f"{p.name}は{message}")
        self.interrupted = True
        return True

    def _wake_player(self) -> None:
        if self.player.statuses.remove("sleep"):
            self.log.add(f"{self.player.name}は目を覚ました。")

    def _damage_player(self, amount: int) -> None:
        self.player.hp = max(0, self.player.hp - amount)
        self.interrupted = True
        self._log_death_once()

    def _log_death_once(self) -> None:
        if self.is_game_over and not self._death_logged:
            self._death_logged = True
            self.log.add(f"{self.player.name}は力尽きた……")

    def _go_down(self) -> None:
        p = self.player
        removed = p.statuses.clear_until_floor_change()
        if "max_hp_down" in removed:
            p.max_hp += removed["max_hp_down"] * self.catalog.statuses["max_hp_down"].value
            self.log.add("最大HPが元に戻った。")
        self.enter_floor(self.floor.number + 1)
        progression.recover_mp_on_descend(p, self.params.survival)

    # --- ターン進行 ---

    def _next_uid(self) -> int:
        self._next_uid_value += 1
        return self._next_uid_value

    def _end_player_action(self) -> None:
        if self.is_game_over:
            return
        self._run_until_player_turn()
        # 眠っている間は、目が覚めるまで時間だけが進む
        while "sleep" in self.player.statuses and not self.is_game_over:
            self._run_until_player_turn()
        self.update_fov()

    def _run_until_player_turn(self) -> None:
        self.scheduler.after_player_action(
            self.player,
            self.floor.monsters,
            act=self._monster_act,
            end_turn=self._on_turn_end,
            stop=lambda: self.is_game_over,
        )

    def _monster_act(self, monster: Any) -> None:
        if self.is_game_over or monster not in self.floor.monsters:
            return
        ai.take_turn(monster, self, self.params.ai)

    def _on_turn_end(self, turn: int) -> None:
        p = self.player
        statuses = self.catalog.statuses
        if "poison" in p.statuses:
            self._damage_player(statuses["poison"].value)
        if "mana_drain" in p.statuses:
            p.mp = max(0, p.mp - statuses["mana_drain"].value)
        for message in progression.apply_turn_end(
            p, turn, self.params.survival, can_regen_hp="poison" not in p.statuses
        ):
            self.log.add(message)
        self._log_death_once()
        if self.is_game_over:
            return

        for status_id in p.statuses.tick():
            definition = statuses[status_id]
            suffix = "が治った。" if definition.kind == AILMENT else "の効果が切れた。"
            self.log.add(f"{definition.name}{suffix}")
        p.speed = speed_for(p.statuses, statuses)
        for monster in self.floor.monsters:
            monster.statuses.tick()

        if turn % self.params.spawn.respawn_interval == 0:
            spawn.respawn_monster(
                self.floor,
                self.rng,
                self.catalog,
                lambda c: self.fog.state(*c) != Visibility.VISIBLE and chebyshev(c, p.pos) > 1,
                self._next_uid,
            )
