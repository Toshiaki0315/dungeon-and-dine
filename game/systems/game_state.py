"""1回の挑戦（ラン）中のゲーム状態と、プレイヤーの行動によるターン進行。

描画や入力から切り離し、テストから直接操作できるようにしている。
pyxel を import しないこと。
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Any

from game import rng as rng_module
from game.data_loader import DataValidationError
from game.entities import ai
from game.entities.ai import AIParams
from game.entities.item import (
    CATEGORY_AMMO,
    GOLD_ID,
    MYSTERY_FOOD_ID,
    Chest,
    Effect,
    FloorItem,
    ItemDef,
    ItemInstance,
    WeaponStats,
)
from game.entities.monster import (
    ABILITY_ON_HIT_STATUS,
    AI_AMBUSH,
    AI_BOSS,
    MODE_CHASE,
    Ability,
    Monster,
)
from game.entities.player import Player, PlayerParams
from game.rng import weighted_choice
from game.systems import progression, spawn
from game.systems.catalog import Catalog
from game.systems.combat import REACH_LINE, CombatParams, CombatStats, reach_cells, roll_attack
from game.systems.cooking import (
    HEAT_CAMPFIRE,
    HEAT_STOVE,
    MAX_MATERIALS,
    MIN_MATERIALS,
    CookingParams,
    CookingPreview,
    Notebook,
    Recipe,
    combination_key,
    ingredient_drop_chance,
    match_recipe,
)
from game.systems.cooking import preview as cooking_preview
from game.systems.equipment import EquipmentBonus, EquipmentParams, compute_bonus
from game.systems.inventory import Inventory
from game.systems.message_log import MessageLog, highlight
from game.systems.meta import BaseCampParams, Loadout
from game.systems.progression import ProgressionParams, SurvivalParams
from game.systems.skills import (
    SKILL_APPRAISE,
    SKILL_ATTACK,
    SKILL_CAMPFIRE,
    SKILL_STEALTH,
    SkillDef,
    skills_up_to_level,
)
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
    TrapDef,
    TrapParams,
    search_around,
)
from game.systems.turn import TurnScheduler
from game.world.direction import Direction, chebyshev
from game.world.floor import Area, Campfire, Floor, area_for_floor
from game.world.fov import FogMap, FovParams, Visibility, compute_visible
from game.world.mapgen import MapGenParams, generate_boss_floor, generate_floor
from game.world.tiles import Tile

Position = tuple[int, int]

# 実装済みの消費アイテムの効果（それ以外は「未実装」と表示して使わない）
IMPLEMENTED_EFFECTS = frozenset(
    {
        "heal", "restore_mp", "restore_mp_full", "cure", "satiety", "inflict", "status",
        "max_hp_up", "mystery_penalty", "recipe_memo", "fire_blast", "identify", "holy_water",
        "uncurse_all", "return",
    }
)  # fmt: skip

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

# UI で演出する出来事（効果音・ポップアップ・画面効果）。仕様書 14章
EFFECT_CURSE = "curse"  # 呪いが発動した（画面を紫に点滅させる）
EFFECT_ROAR = "roar"  # ボスが咆哮した（画面を揺らす）
EFFECT_ATTACK = "attack"
EFFECT_SKILL = "skill"
EFFECT_HIT = "hit"  # ダメージを受けた（value にダメージ量）
EFFECT_PICKUP = "pickup"
EFFECT_COOK = "cook"
EFFECT_LEVEL_UP = "level_up"
EFFECT_STAIRS = "stairs"
EFFECT_DEATH = "death"
EFFECT_CLEAR = "clear"


@dataclass(frozen=True)
class GameEvent:
    """UI に伝える出来事。x, y はマップ上の位置（-1 なら位置を持たない）。"""

    kind: str
    x: int = -1
    y: int = -1
    value: int = 0
    on_player: bool = False


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
    equipment: EquipmentParams
    cooking: CookingParams
    base_camp: BaseCampParams
    fov: FovParams
    inventory_capacity: int
    inventory_stack_max: int
    areas: tuple[Area, ...]
    boss_interval: int  # 何階ごとにボスが出るか（floors.json の "cycle"）
    ending_floor: int  # ここのボスを倒すとエンディング。これより下へも潜れる
    bosses: tuple[str, ...]  # ボスの出る順。一周したら先頭に戻り、深層の強化を受ける

    @classmethod
    def from_data(cls, data: Mapping[str, Mapping[str, Any]]) -> GameParams:
        balance = data["balance"]
        catalog = Catalog.from_data(data)
        cooking = CookingParams.from_dict(balance["cooking"])
        unknown = [
            s for e in cooking.mystery_penalties for s in e.statuses if s not in catalog.statuses
        ]
        if unknown:
            raise DataValidationError(f"cooking: 状態異常がありません: {', '.join(unknown)}")
        return cls(
            catalog=catalog,
            mapgen=MapGenParams.from_dict(balance["mapgen"]),
            player=PlayerParams.from_dict(balance["player"]),
            survival=SurvivalParams.from_dict(balance["survival"]),
            progression=ProgressionParams.from_dict(balance["progression"]),
            combat=CombatParams.from_dict(balance["combat"]),
            spawn=SpawnParams.from_dict(balance["spawn"]),
            ai=AIParams.from_dict(balance["ai"]),
            traps=TrapParams.from_dict(balance["traps"]),
            equipment=EquipmentParams.from_dict(balance["equipment"]),
            cooking=cooking,
            base_camp=BaseCampParams.from_dict(balance["base_camp"]),
            fov=FovParams.from_dict(balance["fov"]),
            inventory_capacity=int(balance["inventory"]["capacity"]),
            inventory_stack_max=int(balance["inventory"]["stack_max"]),
            areas=tuple(Area.from_dict(area) for area in data["floors"]["areas"]),
            boss_interval=int(data["floors"]["cycle"]["boss_interval"]),
            ending_floor=int(data["floors"]["cycle"]["ending_floor"]),
            bosses=tuple(str(b) for b in data["floors"]["bosses"]),
        )

    @property
    def cycle_length(self) -> int:
        """エリア定義が覆う階数。これを1周とし、それより下はくり返す。"""
        return max(area.last_floor for area in self.areas)

    def is_boss_floor(self, floor_number: int) -> bool:
        """20階ごとにボス階。エンディングの階より下でも出続ける。"""
        return floor_number > 0 and floor_number % self.boss_interval == 0

    def boss_for_floor(self, floor_number: int) -> str:
        """その階に出るボスのID。表を使い切ったら先頭へ戻る。"""
        index = floor_number // self.boss_interval - 1
        return self.bosses[index % len(self.bosses)]

    def boss_cycle(self, floor_number: int) -> int:
        """そのボスが何巡目か。1巡目（最初の5体）は0で、強化を受けない。"""
        return (floor_number // self.boss_interval - 1) // len(self.bosses)


class MoveResult(Enum):
    MOVED = auto()
    ATTACKED = auto()  # 移動先に敵がいたので攻撃した
    OPENED = auto()  # 移動先の宝箱を開けた
    BLOCKED = auto()  # 壁などで進めなかった（向きだけ変わる）
    CONFIRM_TRAP = auto()  # 発見済みの罠があるので、確認してから進む


class EquipResult(Enum):
    EQUIPPED = auto()
    UNEQUIPPED = auto()
    NEEDS_CONFIRM = auto()  # 未鑑定、または呪いが判明している装備なので確認が必要
    FAILED = auto()


@dataclass(frozen=True)
class KillCause:
    """敵を倒した手段。食材のドロップに影響する（仕様書 9.1）。"""

    drop_multiplier: float = 1.0  # ナイフで 1.5
    guaranteed_drop: bool = False  # 「解体術」
    fire: bool = False  # 炎属性（火炎の巻物、炎の印）なら焼き〇〇になる


@dataclass(frozen=True)
class CookPlan:
    """調理の結果。カットインで材料を選び終えた時点で決め、画面を戻すときに反映する。"""

    materials: tuple[ItemInstance, ...]
    heat: str  # HEAT_CAMPFIRE / HEAT_STOVE
    matched: Recipe | None  # 材料に一致したレシピ
    success: bool  # False なら謎の物体になる
    product: ItemDef

    @property
    def recipe(self) -> Recipe | None:
        return self.matched if self.success else None


class GameState:
    def __init__(
        self,
        run_seed: int,
        params: GameParams,
        notebook: Notebook | None = None,
        *,
        generate: bool = True,
    ) -> None:
        self.run_seed = run_seed
        self.params = params
        self.catalog = params.catalog
        self.rng = random.Random(run_seed)  # 戦闘や敵AIなど、プレイ中に使う乱数
        self.player = Player.from_params(params.player)
        self.player.skills = skills_up_to_level(self.player.level, self.catalog.skills)
        self.inventory = Inventory(params.inventory_capacity, params.inventory_stack_max)
        self.scheduler = TurnScheduler()
        self.log = MessageLog()
        self.notebook = notebook if notebook is not None else Notebook()  # ランをまたいで残る
        self.interrupted = False  # 連続移動を止めるべき出来事（敵の発見・被ダメージなど）
        self.returned = False  # 帰還の巻物で生還した
        self.cleared = False  # エンディングの階のボスを倒した（挑戦は終わらない）
        self.ending_shown = False  # エンディングを表示済みか（同じ挑戦で二度出さない）
        self.last_boss_name = ""  # 直前に倒したボスの名前（エンディングの文面に使う）
        self.events: list[GameEvent] = []  # UI で演出する出来事（EFFECT_*）
        self._next_uid_value = 0
        self._visible_monster_ids: set[int] = set()
        self._sight: set[Position] = set()  # 敵がプレイヤーに気づける範囲（盲目の影響を受けない）
        self._death_logged = False
        self.floor: Floor
        self.area: Area
        self.fog: FogMap
        if generate:  # 中断データから復元するときは、systems/save.py が状態を入れる
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
    def run_over(self) -> bool:
        """この挑戦が終わったか。

        迷宮から出る方法は「力尽きる」か「帰還の巻物を使う」かの2つだけ（仕様書 5.5 / 6.6）。
        エンディングの階のボスを倒しても挑戦は終わらず、さらに下へ潜り続けられる。
        """
        return self.is_game_over or self.returned

    @property
    def is_boss_floor(self) -> bool:
        return self.params.is_boss_floor(self.floor.number)

    @property
    def boss_alive(self) -> bool:
        return any(m.definition.ai == AI_BOSS for m in self.floor.monsters)

    @property
    def uid_counter(self) -> int:
        """ここまでに配った敵の通し番号。中断データの保存・復元で使う。"""
        return self._next_uid_value

    @uid_counter.setter
    def uid_counter(self, value: int) -> None:
        self._next_uid_value = value

    @property
    def player_pos(self) -> Position:
        return self.player.pos

    @property
    def player_on_stairs(self) -> bool:
        return self.floor.tile_at(*self.player.pos) == Tile.STAIRS_DOWN

    @property
    def can_descend(self) -> bool:
        # ボス階にも階段はあるが、ボスを倒すまでは降りられない
        if self.is_boss_floor and self.boss_alive:
            return False
        return self.player_on_stairs

    @property
    def can_cook(self) -> bool:
        return self.heat_source() is not None

    @property
    def can_talk(self) -> bool:
        """行商人に話しかけられるか（その場か隣の8マス。仕様書 12.4）。"""
        return self.floor.merchant_near(*self.player.pos) is not None

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

    def consume_events(self) -> list[GameEvent]:
        events, self.events = self.events, []
        return events

    def emit(self, kind: str, pos: Position | None = None, value: int = 0, **kwargs: bool) -> None:
        x, y = pos if pos is not None else (-1, -1)
        self.events.append(GameEvent(kind, x, y, value, **kwargs))

    def take_loadout(self, loadout: Loadout) -> None:
        """拠点に置いてある持ち物と装備を持って、挑戦を始める（仕様書 12.3）。"""
        self.inventory.capacity = loadout.items.capacity
        for item in loadout.items.items:
            self.inventory.add(item)
        for slot, item in loadout.equipment.items():
            if item is not None:
                self._set_equipment(slot, item)
        self.update_fov()

    def equipment_bonus(self) -> EquipmentBonus:
        return compute_bonus(self.player.equipment)

    def player_combat_stats(
        self, equipment: Mapping[str, ItemInstance | None] | None = None
    ) -> CombatStats:
        """装備を反映した攻撃側・防御側の能力。equipment を渡すと、その装備で計算する。"""
        p = self.player
        equipment = p.equipment if equipment is None else equipment
        bonus = compute_bonus(equipment)
        weapon_item = equipment.get("weapon")
        weapon = self._weapon_stats(weapon_item)
        weapon_attack = weapon.attack
        if weapon_item is not None and weapon is not self.catalog.unarmed:
            weapon_attack += weapon_item.modifier
        statuses = self.catalog.statuses
        atk_bonus = statuses["atk_up"].value if "atk_up" in p.statuses else 0
        def_bonus = statuses["def_up"].value if "def_up" in p.statuses else 0
        base_crit = (
            weapon.crit_rate if weapon.crit_rate is not None else self.params.combat.crit_rate
        )
        return CombatStats(
            atk=p.atk + weapon_attack + atk_bonus,
            defense=p.defense + bonus.defense + def_bonus,
            hit=p.hit * bonus.hit_percent // 100,
            evade=p.evade,
            crit_rate=base_crit + bonus.crit_bonus,
        )

    def preview_stats(self, slot: str, item: ItemInstance | None) -> CombatStats | None:
        """その部位を item に替えたときの能力。性能が判明していない装備なら None。"""
        if item is not None and not item.identified:
            return None
        equipment = dict(self.player.equipment)
        equipment[slot] = item
        return self.player_combat_stats(equipment)

    def effective_weapon(self) -> WeaponStats:
        """装備中の武器の性能。武器がないとき・矢のない弓は素手として扱う。"""
        return self._weapon_stats(self.player.weapon)

    def item_targets(self, item: ItemInstance) -> list[ItemInstance] | None:
        """使うときに対象を選ぶアイテムなら、選べる装備の一覧。対象のいらないアイテムは None。"""
        types = {effect.type for effect in item.definition.effects}
        if "identify" in types:
            return [i for i in self.inventory.items if i.is_equipment and not i.identified]
        if "holy_water" in types:
            return [i for i in self.inventory.items if i.is_equipment and i is not item]
        return None

    # --- 料理（仕様書 9.3） ---

    def heat_source(self) -> str | None:
        """料理に使える火。焚き火のそばなら焚き火、なければ携帯コンロ（視界に敵がいないとき）。"""
        if self.floor.in_safe_zone(*self.player.pos):
            return HEAT_CAMPFIRE
        if self._usable_stove() is not None and not self._enemy_in_sight():
            return HEAT_STOVE
        return None

    def cooking_unavailable_reason(self) -> str:
        if self._usable_stove() is not None:
            return "敵がいる。携帯コンロを使っている場合ではない。"
        return "焚き火のそばか、携帯コンロがないと料理できない。"

    def cooking_candidates(self) -> list[ItemInstance]:
        """材料にできるアイテム（装備中のものと、火に使う携帯コンロを除く）。"""
        stove = self._usable_stove() if self.heat_source() == HEAT_STOVE else None
        return [
            i for i in self.inventory.items if not self.player.is_equipped(i) and i is not stove
        ]

    def cooking_preview(self, materials: Sequence[ItemInstance]) -> CookingPreview:
        definitions = [m.definition for m in materials]
        return cooking_preview(definitions, self.catalog.recipes.values(), self.notebook)

    def plan_cooking(self, materials: Sequence[ItemInstance]) -> CookPlan | None:
        """選んだ材料での調理の結果を決める。状態は変えず、ターンも進めない。

        材料が2〜3個でない、材料にできないアイテムを含むなどの場合は None を返す。
        """
        heat = self.heat_source()
        candidates = self.cooking_candidates()
        if (
            self.is_game_over
            or heat is None
            or not MIN_MATERIALS <= len(materials) <= MAX_MATERIALS
            or len({id(m) for m in materials}) != len(materials)
            or any(m not in candidates for m in materials)
        ):
            return None
        recipe = match_recipe([m.definition for m in materials], self.catalog.recipes.values())
        success = False
        if recipe is not None:
            fail_chance = self.params.cooking.fail_chance + self.equipment_bonus().cook_fail_bonus
            success = self.rng.randrange(100) >= fail_chance
        product_id = recipe.id if recipe is not None and success else MYSTERY_FOOD_ID
        return CookPlan(tuple(materials), heat, recipe, success, self.catalog.items[product_id])

    def apply_cooking(self, plan: CookPlan) -> bool:
        """調理の結果を反映する（1ターン消費）。材料は成否にかかわらず消費する。"""
        if self.is_game_over or any(m not in self.inventory.items for m in plan.materials):
            return False
        p = self.player
        names = "・".join(highlight(m.definition.name) for m in plan.materials)
        for material in plan.materials:
            self.inventory.take_one(material)
        if plan.heat == HEAT_STOVE:
            self._use_stove()

        self.emit(EFFECT_COOK)
        self.log.add(f"{p.name}は{names}を料理した。")
        product = ItemInstance(plan.product)
        if plan.recipe is not None:
            self.log.add(f"{highlight(product.name)}ができた！")
            if self.notebook.discover(plan.recipe.id):
                self.log.add("新しいレシピを手帳に書き留めた。")
        else:
            self.log.add(f"{highlight(product.name)}ができた……")
            if plan.matched is None:
                self.notebook.record_failure(combination_key(m.definition for m in plan.materials))
        if not self.inventory.add(product):
            self.log.add(f"持ちきれない。{highlight(product.name)}を足元に置いた。")
            self._drop_to_floor(product, p.pos)
        self._end_player_action()
        return True

    def skill_targets(self, skill_id: str) -> list[ItemInstance] | None:
        if self.catalog.skills[skill_id].type != SKILL_APPRAISE:
            return None
        return [
            i
            for i in self.inventory.items
            if i.is_equipment and not i.identified and not i.curse_known
        ]

    # --- 階層 ---

    def enter_floor(self, number: int) -> None:
        floor_rng = rng_module.floor_rng(self.run_seed, number)
        if self.params.is_boss_floor(number):
            # 20階ごとのボス階。固定レイアウトにする（仕様書 5.3 / 8.3）
            self.floor = generate_boss_floor(number, self.params.mapgen)
            spawn.populate_boss_floor(
                self.floor,
                self.catalog,
                self._next_uid,
                self.params.boss_for_floor(number),
                self.params.spawn,
                self.params.boss_cycle(number),
            )
        else:
            self.floor = generate_floor(floor_rng, number, self.params.mapgen)
            spawn.populate_floor(
                self.floor,
                floor_rng,
                self.catalog,
                self.params.spawn,
                self.params.equipment,
                self._next_uid,
                cooking=self.params.cooking,
            )
        self.area = area_for_floor(self.params.areas, number)
        self.fog = FogMap(self.floor.width, self.floor.height)
        self.player.x, self.player.y = self.floor.start
        self._visible_monster_ids = set()
        self.update_fov()

    def update_fov(self) -> None:
        p = self.player
        sight = self.equipment_bonus().sight_bonus
        if "sight_up" in p.statuses:
            sight += self.catalog.statuses["sight_up"].value
        base = self.params.fov
        fov = replace(base, corridor_adjacent=max(0, base.corridor_adjacent + sight))
        visible = compute_visible(self.floor, p.x, p.y, p.facing, fov)
        if "blind" in p.statuses:
            self.fog.update(compute_visible(self.floor, p.x, p.y, p.facing, fov, blind=True))
        else:
            self.fog.update(visible)
        self._sight = visible

        visible_ids = {m.uid for m in self.visible_monsters() if not m.disguised}
        if visible_ids - self._visible_monster_ids:
            self.interrupted = True
        self._visible_monster_ids = visible_ids

    # --- プレイヤーの行動（ターンを消費する） ---

    def move_player(self, direction: Direction, *, confirm_trap: bool = False) -> MoveResult:
        """1歩進む。移動先に敵がいれば攻撃し、宝箱があれば開ける。壁なら向きだけ変わる。"""
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
        chest = self.floor.chest_at(*target)
        if chest is not None:
            p.facing = direction
            if chest.opened:
                self.update_fov()
                return MoveResult.BLOCKED
            self._open_chest(chest)
            return MoveResult.OPENED
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
        """向いている方向へ攻撃する。目の前に宝箱があれば開ける（調べる）。"""
        if self.is_game_over:
            return
        p = self.player
        if "confusion" in p.statuses:
            p.facing = self.rng.choice(list(Direction))
        front = (p.x + p.facing.dx, p.y + p.facing.dy)
        chest = self.floor.chest_at(*front)
        if (
            chest is not None
            and not chest.opened
            and self.floor.monster_at(*front) is None
            and self.floor.can_move(p.x, p.y, p.facing)
        ):
            self._open_chest(chest)
            return
        self._attack_forward()

    def wait(self) -> None:
        """足踏みして1ターン経過させ、周囲の罠を探す。"""
        if self.is_game_over:
            return
        p = self.player
        bonus = self.equipment_bonus()
        if not bonus.no_trap_find:
            chance = self.params.traps.search_chance + bonus.trap_find_bonus
            for trap in search_around(self.floor, p.x, p.y, self.rng, chance):
                self.log.add(f"{highlight(trap.name)}を見つけた。")
                self.interrupted = True
        self._end_player_action()

    def use_skill(self, skill_id: str, target: ItemInstance | None = None) -> bool:
        """スキルを使う。使えなかったとき（MP不足など）はターンを消費せず False を返す。"""
        p = self.player
        if self.is_game_over or skill_id not in p.skills:
            return False
        skill = self.catalog.skills[skill_id]
        if skill.type not in (SKILL_ATTACK, SKILL_STEALTH, SKILL_APPRAISE, SKILL_CAMPFIRE):
            self.log.add(f"「{skill.name}」は未実装です。")
            return False
        if self.equipment_bonus().skill_seal:
            self.log.add("呪いのせいで、スキルが使えない！")
            return False
        if p.mp < skill.mp:
            self.log.add("MPが足りない。")
            return False
        targets = self.skill_targets(skill_id)
        if targets is not None and target not in targets:
            return False
        kindle_cell: Position | None = None
        if skill.type == SKILL_CAMPFIRE:
            kindle_cell = self._kindle_cell()
            if kindle_cell is None:
                return False

        p.mp -= skill.mp
        self.emit(EFFECT_SKILL)
        self.log.add(f"{p.name}は「{skill.name}」を使った！")
        if skill.type == SKILL_ATTACK:
            if "confusion" in p.statuses:
                p.facing = self.rng.choice(list(Direction))
            cells = reach_cells(self.floor, p.x, p.y, p.facing, skill.area or "front")
            monsters = self._monsters_in(cells, first_only=False)
            if not monsters:
                self.log.add("しかし、そこには何もいなかった。")
            cause = self._melee_cause(guaranteed_drop=skill.guaranteed_drop)
            for monster in monsters:
                self._player_hits(monster, multiplier=skill.multiplier, cause=cause)
            if skill.self_damage_ratio > 0:
                recoil = max(1, math.floor(p.max_hp * skill.self_damage_ratio))
                self.log.add(f"{p.name}は反動で{recoil}のダメージを受けた。")
                self._damage_player(recoil)
        elif skill.type == SKILL_STEALTH:
            p.statuses.add(self.catalog.statuses["stealth"], skill.duration)
        elif skill.type == SKILL_CAMPFIRE:
            assert kindle_cell is not None
            expires_at = self.turn + skill.duration
            self.floor.campfires.append(Campfire(*kindle_cell, expires_at=expires_at))
            self.floor.kindled = True
            self.log.add("焚き火を起こした。")
        else:
            assert target is not None
            target.curse_known = True
            verdict = "呪われている！" if target.cursed else "呪われていない。"
            self.log.add(f"{highlight(target.name)}は{verdict}")
        self._end_player_action()
        return True

    def use_item(self, item: ItemInstance, target: ItemInstance | None = None) -> bool:
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
        targets = self.item_targets(item)
        if targets is not None and target not in targets:
            return False

        self.inventory.take_one(item)
        verb = {"食べる": "食べた", "読む": "読んだ"}.get(label, "使った")
        self.log.add(f"{self.player.name}は{highlight(definition.name)}を{verb}。")
        for effect in definition.effects:
            self._apply_item_effect(effect, target)
        self._end_player_action()
        return True

    def throw_item(self, item: ItemInstance) -> bool:
        """向いている方向の直線上に投げる。最初に当たった敵にダメージを与える。"""
        if self.is_game_over or item not in self.inventory.items:
            return False
        if not self._release_if_equipped(item):
            return False
        p = self.player
        thrown = self.inventory.take_one(item)
        if "confusion" in p.statuses:
            p.facing = self.rng.choice(list(Direction))
        self.log.add(f"{p.name}は{highlight(thrown.name)}を投げた。")

        landing = p.pos
        hit = False
        cells = reach_cells(
            self.floor, p.x, p.y, p.facing, REACH_LINE, self.params.combat.throw_range
        )
        for cell in cells:
            if self.floor.chest_at(*cell) is not None:
                break
            monster = self.floor.monster_at(*cell)
            if monster is not None:
                self._reveal_if_disguised(monster)
                self._damage_monster(monster, self.params.combat.throw_damage)
                hit = True
                break
            landing = cell
        if not hit and not self._drop_to_floor(thrown, landing):
            self.log.add(f"{highlight(thrown.name)}はどこかへ消えてしまった。")
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
        if not self._release_if_equipped(item):
            return False
        self.inventory.remove(item)
        self.floor.items.append(FloorItem(item, *p.pos))
        self.log.add(f"{highlight(item.name)}を足元に置いた。")
        self._end_player_action()
        return True

    def equip(self, item: ItemInstance, *, confirmed: bool = False) -> EquipResult:
        """装備する（1ターン消費）。装備すると性能がすべて判明し、呪われていれば発動する。"""
        if self.is_game_over or item not in self.inventory.items or not item.is_equipment:
            return EquipResult.FAILED
        p = self.player
        slot = item.definition.slot
        assert slot is not None
        current = p.equipment[slot]
        if current is item:
            return self.unequip(item)
        if current is not None and current.cursed:
            self._log_cannot_remove(current)
            return EquipResult.FAILED
        if not confirmed and (not item.identified or (item.curse_known and item.cursed)):
            return EquipResult.NEEDS_CONFIRM

        self._set_equipment(slot, item)
        item.identified = True
        item.curse_known = True
        self.log.add(f"{p.name}は{highlight(item.name)}を装備した。")
        if item.curse is not None:
            self.log.add(
                f"{highlight(item.name)}は呪われていた！ 「{item.curse.name}」の呪いがかかった。"
            )
            self.emit(EFFECT_CURSE)
            self.interrupted = True
        self._end_player_action()
        return EquipResult.EQUIPPED

    def unequip(self, item: ItemInstance) -> EquipResult:
        """装備を外す（1ターン消費）。呪われていると外せない。"""
        slot = item.definition.slot
        if self.is_game_over or slot is None or self.player.equipment.get(slot) is not item:
            return EquipResult.FAILED
        if item.cursed:
            self._log_cannot_remove(item)
            return EquipResult.FAILED
        self._set_equipment(slot, None)
        self.log.add(f"{self.player.name}は{highlight(item.name)}を外した。")
        self._end_player_action()
        return EquipResult.UNEQUIPPED

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
            and self.floor.chest_at(x, y) is None
            and not self.floor.in_safe_zone(x, y)  # 焚き火の周囲には入らない
            and self.floor.merchant_at(x, y) is None  # 行商人のマスにも入らない
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
        block_rate = self.equipment_bonus().block_rate
        if block_rate > 0 and self.rng.randrange(100) < block_rate:
            self.log.add(f"{monster.name}の攻撃を盾で防いだ！")
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

    def monster_roar(self, monster: Monster, ability: Ability) -> None:
        """ボスの咆哮。周囲のプレイヤーを鈍足にする（仕様書 8.3）。"""
        self.log.add(f"{monster.name}が咆哮した！")
        self.emit(EFFECT_ROAR)
        self.interrupted = True
        if ability.status is not None and chebyshev(monster.pos, self.player.pos) <= ability.range:
            self._inflict_player(ability.status, ability.chance)

    def monster_devour(self, monster: Monster, ability: Ability) -> None:
        """ボスの捕食。満腹度を奪い、そのぶん自分の HP を回復する（仕様書 8.3）。"""
        p = self.player
        amount = min(p.satiety, ability.value)
        p.satiety -= amount
        monster.hp = min(monster.max_hp, monster.hp + amount)
        self.log.add(f"{monster.name}は{p.name}に喰らいついた！ 満腹度を{amount}奪われた。")
        self.interrupted = True

    def reveal_monster(self, monster: Monster) -> None:
        self._reveal_if_disguised(monster)

    # --- 内部処理: 攻撃 ---

    def _weapon_stats(self, item: ItemInstance | None) -> WeaponStats:
        weapon = item.definition.weapon if item is not None else None
        if weapon is None or (weapon.uses_arrows and self._arrows() is None):
            return self.catalog.unarmed
        return weapon

    def _attack_forward(self) -> None:
        p = self.player
        self.emit(EFFECT_ATTACK)
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
        cause = self._melee_cause()
        for monster in targets:
            self._player_hits(monster, cause=cause)
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

    def _melee_cause(self, *, guaranteed_drop: bool = False) -> KillCause:
        return KillCause(
            drop_multiplier=self.effective_weapon().ingredient_drop_multiplier,
            guaranteed_drop=guaranteed_drop,
            fire=self.equipment_bonus().fire_attack,
        )

    def _player_hits(
        self, monster: Monster, multiplier: float = 1.0, cause: KillCause | None = None
    ) -> None:
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
        self._damage_monster(monster, result.damage, critical=result.critical, cause=cause)

    def _damage_monster(
        self,
        monster: Monster,
        damage: int,
        *,
        critical: bool = False,
        cause: KillCause | None = None,
    ) -> None:
        monster.hp -= damage
        self.emit(EFFECT_HIT, monster.pos, damage)
        prefix = "会心の一撃！ " if critical else ""
        self.log.add(f"{prefix}{monster.name}に{damage}のダメージ。")
        if monster.hp <= 0:
            self._kill_monster(monster, cause or KillCause())
        else:
            self._alert(monster)

    def _alert(self, monster: Monster) -> None:
        """攻撃された敵はプレイヤーに気づく。"""
        monster.mode = MODE_CHASE
        monster.target = self.player.pos

    def _kill_monster(self, monster: Monster, cause: KillCause) -> None:
        if monster in self.floor.monsters:
            self.floor.monsters.remove(monster)
        exp = monster.definition.exp
        self.log.add(f"{monster.name}を倒した！ {exp}の経験値を得た。")
        level_before = self.player.level
        for message in progression.gain_exp(
            self.player, exp, self.params.progression, self.catalog.skills
        ):
            self.log.add(message)
        if self.player.level > level_before:
            self.emit(EFFECT_LEVEL_UP, self.player.pos)
        if monster.definition.ai == AI_BOSS:
            self.emit(EFFECT_CLEAR)
            self.last_boss_name = monster.name
            if self.floor.number >= self.params.ending_floor:
                self.cleared = True
                self.log.add(f"{monster.name}を倒した！ 迷宮の主は崩れ落ちた。")
            else:
                self.log.add(f"{monster.name}を倒した！ さらに下へ続く道が現れた。")
        if monster.definition.ai == AI_AMBUSH:
            # ミミックは宝箱の中身を落とす
            contents = spawn.chest_contents(
                self.rng, self.catalog, self.floor.number, self.params.spawn, self.params.equipment
            )
            if self._drop_to_floor(contents, monster.pos):
                self.log.add(f"{monster.name}は{highlight(contents.name)}を落とした。")
        self._drop_ingredient(monster, cause)
        if self.rng.randrange(100) < self.params.spawn.monster_gold_drop_chance:
            amount = spawn.gold_amount(self.rng, self.floor.number, self.params.spawn)
            self._drop_to_floor(ItemInstance(self.catalog.items[GOLD_ID], amount), monster.pos)

    def _drop_ingredient(self, monster: Monster, cause: KillCause) -> None:
        drop_id = monster.definition.drop
        if drop_id is None:
            return
        chance = ingredient_drop_chance(
            self.params.cooking.drop_chance,
            cause.drop_multiplier,
            guaranteed=cause.guaranteed_drop,
        )
        if chance < 100 and self.rng.randrange(100) >= chance:
            return
        definition = self.catalog.items[drop_id]
        if cause.fire and definition.grilled_id is not None:
            definition = self.catalog.items[definition.grilled_id]
        item = self.new_item(definition)
        if self._drop_to_floor(item, monster.pos):
            self.log.add(f"{monster.name}は{highlight(item.name)}を落とした。")

    def new_item(self, definition: ItemDef) -> ItemInstance:
        """ラン中に手に入るアイテムの個体。生肉はこの時点から腐るまでの時間を数える。"""
        rot_at = None
        if definition.rotten_id is not None:
            rot_at = self.turn + self.params.cooking.rot_turns
        return ItemInstance(definition, rot_at=rot_at)

    def _reveal_if_disguised(self, monster: Monster) -> None:
        if not monster.disguised:
            return
        monster.disguised = False
        self._alert(monster)
        self.log.add(f"{highlight('宝箱')}は{monster.name}だった！")
        self.interrupted = True

    # --- 内部処理: アイテム・装備 ---

    def _arrows(self) -> ItemInstance | None:
        return next(
            (i for i in self.inventory.items if i.definition.category == CATEGORY_AMMO), None
        )

    def _apply_item_effect(self, effect: Effect, target: ItemInstance | None) -> None:
        p = self.player
        if effect.type == "heal":
            before = p.hp
            p.hp = min(p.max_hp, p.hp + effect.value)
            self.log.add(f"HPが{p.hp - before}回復した。")
        elif effect.type == "restore_mp":
            before = p.mp
            p.mp = min(p.max_mp, p.mp + effect.value)
            self.log.add(f"MPが{p.mp - before}回復した。")
        elif effect.type == "restore_mp_full":
            p.mp = p.max_mp
            self.log.add("MPが全回復した。")
        elif effect.type == "cure":
            cured: list[str] = []
            for status_id in effect.statuses:
                stacks = p.statuses.stacks(status_id)
                if not p.statuses.remove(status_id):
                    continue
                cured.append(self.catalog.statuses[status_id].name)
                if status_id == "max_hp_down":
                    p.max_hp += stacks * self.catalog.statuses[status_id].value
            self.log.add(f"{'・'.join(cured)}が治った。" if cured else "何も起こらなかった。")
            p.speed = speed_for(p.statuses, self.catalog.statuses)
        elif effect.type == "satiety":
            p.satiety = max(0, min(p.max_satiety, p.satiety + effect.value))
            self.log.add("おなかがふくれた。" if effect.value >= 0 else "おなかが減ってしまった。")
        elif effect.type == "inflict":
            for status_id in effect.statuses:
                self._inflict_player(status_id, effect.chance)
        elif effect.type == "status":
            for status_id in effect.statuses:
                definition = self.catalog.statuses[status_id]
                p.statuses.add(definition)
                self.log.add(f"{definition.name}の効果がついた。")
            p.speed = speed_for(p.statuses, self.catalog.statuses)
            self.update_fov()
        elif effect.type == "max_hp_up":
            p.max_hp += effect.value
            p.hp += effect.value
            self.log.add(f"最大HPが{effect.value}上がった。")
        elif effect.type == "mystery_penalty":
            penalties = self.params.cooking.mystery_penalties
            if penalties:
                self._apply_item_effect(self.rng.choice(penalties), None)
        elif effect.type == "recipe_memo":
            self._read_memo()
        elif effect.type == "fire_blast":
            self.log.add("炎が巻き起こった！")
            for monster in list(self.floor.monsters):
                if chebyshev(monster.pos, p.pos) <= effect.radius:
                    self._reveal_if_disguised(monster)
                    self._damage_monster(monster, effect.value, cause=KillCause(fire=True))
        elif effect.type == "identify" and target is not None:
            before = target.name
            target.identified = True
            target.curse_known = True
            self.log.add(f"{highlight(before)}は{highlight(target.name)}だった。")
            if target.cursed:
                self.log.add("呪われている！")
        elif effect.type == "holy_water" and target is not None:
            was_cursed = target.cursed
            target.curse = None
            target.curse_known = True
            target.modifier += 1
            if was_cursed:
                self.log.add(f"{highlight(target.name)}の呪いが解けた。")
            self.log.add(f"{highlight(target.name)}に聖なる力が宿った。")
            self.update_fov()
        elif effect.type == "return":
            self.returned = True
            self.log.add(f"{p.name}は光に包まれ、地上へ引き上げられた。")
        elif effect.type == "uncurse_all":
            cursed = [item for item in p.equipped_items() if item.cursed]
            for item in cursed:
                item.curse = None
                item.curse_known = True
            self.log.add("装備の呪いが解けた。" if cursed else "しかし、何も起こらなかった。")
            self.update_fov()

    def _read_memo(self) -> None:
        """先人のメモ: 未発見のレシピを1つ手帳に登録する。なければお金をもらう。"""
        unknown = [
            r for r in self.catalog.recipes.values() if not self.notebook.is_discovered(r.id)
        ]
        if not unknown:
            self.player.gold += self.params.cooking.memo_gold
            self.log.add(
                f"知っているレシピばかりだ。挟まっていた{self.params.cooking.memo_gold}Gを手に入れた。"
            )
            return
        recipe = self.rng.choice(unknown)
        self.notebook.discover(recipe.id)
        self.log.add(f"手帳に「{highlight(recipe.name)}」のレシピを書き写した。")

    def _usable_stove(self) -> ItemInstance | None:
        return next(
            (i for i in self.inventory.items if i.definition.charges > 0 and (i.charges or 0) > 0),
            None,
        )

    def _use_stove(self) -> None:
        stove = self._usable_stove()
        if stove is None:
            return
        stove.charges = (stove.charges or 0) - 1
        if stove.charges <= 0:
            self.inventory.remove(stove)
            self.log.add(f"{highlight(stove.definition.name)}は壊れてしまった。")

    def _enemy_in_sight(self) -> bool:
        return any(not m.disguised for m in self.visible_monsters())

    def _kindle_cell(self) -> Position | None:
        """「火起こし」で焚き火を作るマス（向いている方向の隣）。作れなければログを出して None。"""
        p, floor = self.player, self.floor
        if floor.kindled:
            self.log.add("この階では、もう火を起こせない。")
            return None
        cell = (p.x + p.facing.dx, p.y + p.facing.dy)
        if (
            not floor.can_move(p.x, p.y, p.facing)
            or floor.tile_at(*cell) == Tile.STAIRS_DOWN
            or floor.monster_at(*cell) is not None
            or floor.chest_at(*cell) is not None
            or floor.item_at(*cell) is not None
            or floor.campfire_at(*cell) is not None
        ):
            self.log.add("そこには火を起こせない。")
            return None
        return cell

    def _set_equipment(self, slot: str, item: ItemInstance | None) -> None:
        """部位の装備を差し替え、鎧による最大HPの増減を反映する。"""
        p = self.player
        old = p.equipment[slot]
        if old is not None and old.definition.armor is not None:
            p.max_hp = max(1, p.max_hp - old.definition.armor.max_hp_bonus)
            p.hp = min(p.hp, p.max_hp)
        p.equipment[slot] = item
        if item is not None and item.definition.armor is not None:
            p.max_hp += item.definition.armor.max_hp_bonus
        self.update_fov()

    def _release_if_equipped(self, item: ItemInstance) -> bool:
        """投げる・捨てる前に、装備中なら外す。呪われていて外せなければ False。"""
        if not self.player.is_equipped(item):
            return True
        if item.cursed:
            self._log_cannot_remove(item)
            return False
        assert item.definition.slot is not None
        self._set_equipment(item.definition.slot, None)
        return True

    def _log_cannot_remove(self, item: ItemInstance) -> None:
        item.curse_known = True
        self.log.add(f"{highlight(item.name)}は呪われていて外せない！")

    def _open_chest(self, chest: Chest) -> None:
        chest.opened = True
        self.log.add(f"{self.player.name}は{highlight('宝箱')}を開けた。")
        self._receive(chest.contents)
        if chest.trapped:
            trap_id = weighted_choice(
                self.rng, {t.id: t.spawn_weight for t in self.catalog.traps.values()}
            )
            if trap_id is not None:
                trap = self.catalog.traps[trap_id]
                self.log.add(f"{highlight(trap.name)}が仕掛けられていた！")
                self.interrupted = True
                self._apply_trap_effect(trap)
        self._end_player_action()

    def _receive(self, item: ItemInstance) -> None:
        """宝箱などから手に入れる。持ちきれなければ足元に置く。"""
        p = self.player
        name = item.name
        if item.id == GOLD_ID:
            p.gold += item.count
            self.log.add(f"{item.count}Gを手に入れた。")
        elif self.inventory.add(item):
            self.log.add(f"{highlight(name)}を手に入れた。")
        else:
            self.log.add(f"持ちきれない。{highlight(name)}を足元に置いた。")
            self._drop_to_floor(item, p.pos)

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
            self.emit(EFFECT_PICKUP, p.pos)
            self.log.add(f"{item.count}Gを拾った。")
        elif self.inventory.add(item):
            self.floor.items.remove(floor_item)
            self.emit(EFFECT_PICKUP, p.pos)
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
            and self.floor.chest_at(*cell) is None
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
        trap.discovered = True
        self.interrupted = True
        self.log.add(f"{highlight(trap.name)}を踏んだ！")
        avoid_rate = self.equipment_bonus().trap_avoid_rate
        if avoid_rate > 0 and self.rng.randrange(100) < avoid_rate:
            self.log.add("しかし、罠は作動しなかった。")
            return
        self._apply_trap_effect(trap.definition)

    def _apply_trap_effect(self, definition: TrapDef) -> None:
        p = self.player
        if definition.effect == TRAP_PIT:
            self.log.add(f"{p.name}は{definition.damage}のダメージを受けた。")
            self._damage_player(definition.damage)
            if not self.is_game_over and not self.is_boss_floor:
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
            self._rust_equipment(definition.value)
        elif definition.effect == TRAP_ALARM:
            self.log.add("けたたましい音が鳴り響いた！")
            for monster in self.floor.monsters:
                self._alert(monster)

    def _rust_equipment(self, amount: int) -> None:
        """装備中の武器か防具1つの修正値を下げる。「頑丈」の印があれば錆びない。"""
        equipped = self.player.equipped_items()
        if not equipped:
            self.log.add("しかし、錆びるものを身につけていなかった。")
            return
        item = self.rng.choice(equipped)
        if item.mark is not None and item.mark.sturdy:
            self.log.add(f"{highlight(item.name)}は頑丈なので錆びなかった。")
            return
        item.modifier += amount
        self.log.add(f"{highlight(item.definition.name)}が錆びてしまった。")

    def _inflict_player(self, status_id: str, chance: int = 100) -> bool:
        p = self.player
        definition = self.catalog.statuses[status_id]
        resist_all = self.equipment_bonus().status_resist
        if not try_inflict(p.statuses, definition, self.rng, chance, resist_all=resist_all):
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
        self.emit(EFFECT_HIT, self.player.pos, amount, on_player=True)
        self.player.hp = max(0, self.player.hp - amount)
        self.interrupted = True
        self._log_death_once()

    def _log_death_once(self) -> None:
        if self.is_game_over and not self._death_logged:
            self._death_logged = True
            self.emit(EFFECT_DEATH)
            self.log.add(f"{self.player.name}は力尽きた……")

    def _go_down(self) -> None:
        p = self.player
        self.emit(EFFECT_STAIRS)
        removed = p.statuses.clear_until_floor_change()
        if "max_hp_down" in removed:
            p.max_hp += removed["max_hp_down"] * self.catalog.statuses["max_hp_down"].value
            self.log.add("最大HPが元に戻った。")
        self.enter_floor(self.floor.number + 1)
        progression.recover_mp_on_descend(p, self.params.survival)

    # --- ターン進行 ---

    def _rot_items(self, turn: int) -> None:
        """腐る時間になった生肉を、腐った肉に変える（持ち物と、この階の床）。"""

        def rotten(item: ItemInstance) -> ItemInstance | None:
            rotten_id = item.definition.rotten_id
            if item.rot_at is None or rotten_id is None or turn < item.rot_at:
                return None
            return ItemInstance(self.catalog.items[rotten_id])

        items = self.inventory.items
        for index, item in enumerate(items):
            replacement = rotten(item)
            if replacement is not None:
                items[index] = replacement
                self.log.add(f"{highlight(item.name)}が腐ってしまった。")
        for floor_item in self.floor.items:
            replacement = rotten(floor_item.item)
            if replacement is not None:
                floor_item.item = replacement

    def _next_uid(self) -> int:
        self._next_uid_value += 1
        return self._next_uid_value

    def _end_player_action(self) -> None:
        if self.run_over:
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
            p,
            turn,
            self.params.survival,
            self.equipment_bonus().hunger_rate_percent,
            can_regen_hp="poison" not in p.statuses,
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
        self._rot_items(turn)
        for campfire in list(self.floor.campfires):
            if campfire.expires_at is not None and turn >= campfire.expires_at:
                self.floor.campfires.remove(campfire)
                self.log.add("焚き火が消えた。")

        if not self.is_boss_floor and turn % self.params.spawn.respawn_interval == 0:
            spawn.respawn_monster(
                self.floor,
                self.rng,
                self.catalog,
                lambda c: self.fog.state(*c) != Visibility.VISIBLE and chebyshev(c, p.pos) > 1,
                self._next_uid,
                self.params.spawn,
            )
