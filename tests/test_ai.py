import random
from dataclasses import replace

from game import data_loader
from game.entities import ai
from game.entities.ai import AIParams, can_melee, find_next_step
from game.entities.monster import MODE_CHASE, MODE_IDLE, MODE_WANDER, Monster
from game.systems.catalog import Catalog
from game.world.direction import Direction, chebyshev
from tests.helpers import make_floor

DATA = data_loader.load_all()
CATALOG = Catalog.from_data(DATA)
PARAMS = AIParams.from_dict(DATA["balance"]["ai"])

OPEN = [
    "##########",
    "#........#",
    "#........#",
    "#........#",
    "#........#",
    "##########",
]


class FakeContext:
    def __init__(self, floor, player_pos, *, sees=True):
        self.floor = floor
        self.rng = random.Random(0)
        self._player = player_pos
        self.sees = sees
        self.stealthy = False
        self.attacks = []
        self.breaths = []

    @property
    def player_pos(self):
        return self._player

    def can_see_player(self, monster):
        return self.sees

    def player_is_stealthy(self):
        return self.stealthy

    def is_free_for_monster(self, x, y):
        return (
            self.floor.is_walkable(x, y)
            and self.floor.monster_at(x, y) is None
            and (x, y) != self._player
        )

    def move_monster(self, monster, direction):
        if self.is_free_for_monster(monster.x + direction.dx, monster.y + direction.dy):
            monster.try_move(self.floor, direction)

    def monster_attack(self, monster):
        self.attacks.append(monster)

    def monster_breath(self, monster, ability):
        self.breaths.append(monster)

    def reveal_monster(self, monster):
        monster.disguised = False
        monster.mode = MODE_CHASE


def spawn(floor, monster_id, x, y):
    monster = Monster.spawn(CATALOG.monsters[monster_id], x, y, uid=len(floor.monsters) + 1)
    floor.monsters.append(monster)
    return monster


def run_turns(monster, ctx, count, params=PARAMS):
    for _ in range(count):
        ai.take_turn(monster, ctx, params)


def test_chase_monster_attacks_when_adjacent():
    floor = make_floor(OPEN)
    rat = spawn(floor, "giant_rat", 3, 2)
    ctx = FakeContext(floor, (4, 3))
    run_turns(rat, ctx, 1)
    assert ctx.attacks == [rat]
    assert rat.pos == (3, 2)


def test_chase_monster_walks_around_walls_to_player():
    floor = make_floor(
        [
            "#########",
            "#.......#",
            "#.#####.#",
            "#.......#",
            "#########",
        ]
    )
    rat = spawn(floor, "giant_rat", 4, 1)
    ctx = FakeContext(floor, (4, 3))
    for _ in range(10):
        if ctx.attacks:
            break
        run_turns(rat, ctx, 1)
    assert ctx.attacks
    assert chebyshev(rat.pos, (4, 3)) == 1


def test_diagonal_melee_is_blocked_by_corner():
    floor = make_floor(["#####", "#.#.#", "#...#", "#####"])
    assert not can_melee(floor, (1, 2), (2, 1))
    assert can_melee(floor, (1, 2), (2, 2))


def test_chase_monster_idles_until_it_sees_player():
    floor = make_floor(OPEN)
    rat = spawn(floor, "giant_rat", 1, 1)
    ctx = FakeContext(floor, (8, 4), sees=False)
    run_turns(rat, ctx, 3)
    assert rat.pos == (1, 1)
    assert rat.mode == MODE_IDLE


def test_monster_goes_to_last_seen_position_then_gives_up():
    floor = make_floor(OPEN)
    rat = spawn(floor, "giant_rat", 1, 1)
    ctx = FakeContext(floor, (5, 1))
    run_turns(rat, ctx, 1)
    assert rat.target == (5, 1)
    ctx.sees = False
    ctx._player = (8, 4)
    run_turns(rat, ctx, 10)
    assert rat.target is None
    assert rat.mode == MODE_IDLE
    assert chebyshev(rat.pos, (5, 1)) <= 1


def test_wander_monster_moves_randomly_without_sight():
    floor = make_floor(OPEN)
    slime = spawn(floor, "slime", 4, 2)
    ctx = FakeContext(floor, (8, 4), sees=False)
    positions = set()
    for _ in range(10):
        run_turns(slime, ctx, 1)
        positions.add(slime.pos)
    assert len(positions) > 1
    assert slime.mode == MODE_WANDER


def test_stealth_hides_player_from_wandering_monsters():
    floor = make_floor(OPEN)
    slime = spawn(floor, "slime", 1, 1)
    ctx = FakeContext(floor, (3, 1))
    ctx.stealthy = True
    run_turns(slime, ctx, 1)
    assert slime.mode == MODE_WANDER
    assert slime.target is None


def test_erratic_monster_moves_randomly():
    floor = make_floor(OPEN)
    bat = spawn(floor, "cave_bat", 4, 2)
    ctx = FakeContext(floor, (4, 3))
    always_random = replace(PARAMS, erratic_move_chance=100)
    run_turns(bat, ctx, 1, always_random)
    assert ctx.attacks == []
    assert bat.pos != (4, 2)


def test_ranged_monster_breathes_in_straight_line():
    floor = make_floor(OPEN)
    lizard = spawn(floor, "fire_lizard", 1, 1)
    ctx = FakeContext(floor, (4, 4))  # 斜め3マス
    run_turns(lizard, ctx, 1)
    assert ctx.breaths == [lizard]


def test_ranged_monster_does_not_breathe_through_walls_or_out_of_range():
    floor = make_floor(["#########", "#...#...#", "#########"])
    lizard = spawn(floor, "fire_lizard", 1, 1)
    ctx = FakeContext(floor, (3, 1))
    ctx._player = (6, 1)
    run_turns(lizard, ctx, 1)
    assert ctx.breaths == []

    floor = make_floor(["##########", "#........#", "##########"])
    lizard = spawn(floor, "fire_lizard", 1, 1)
    ctx = FakeContext(floor, (7, 1))  # 6マス先
    run_turns(lizard, ctx, 1)
    assert ctx.breaths == []


def test_ranged_monster_steps_away_when_adjacent():
    floor = make_floor(OPEN)
    lizard = spawn(floor, "fire_lizard", 4, 2)
    ctx = FakeContext(floor, (4, 3))
    run_turns(lizard, ctx, 1)
    assert chebyshev(lizard.pos, (4, 3)) == 2
    assert ctx.attacks == []


def test_flee_monster_runs_away_at_low_hp():
    floor = make_floor(OPEN)
    hound = spawn(floor, "labyrinth_hound", 4, 2)
    ctx = FakeContext(floor, (4, 3))
    run_turns(hound, ctx, 1)
    assert ctx.attacks == [hound]

    hound.hp = int(hound.max_hp * PARAMS.flee_hp_ratio)
    run_turns(hound, ctx, 1)
    assert chebyshev(hound.pos, (4, 3)) == 2


def test_mimic_waits_disguised_until_player_is_adjacent():
    floor = make_floor(OPEN)
    mimic = spawn(floor, "mimic", 4, 2)
    assert mimic.disguised and mimic.sprite_name == "chest_closed"
    ctx = FakeContext(floor, (7, 2))
    run_turns(mimic, ctx, 3)
    assert mimic.disguised and mimic.pos == (4, 2)

    ctx._player = (5, 2)
    run_turns(mimic, ctx, 1)
    assert not mimic.disguised
    run_turns(mimic, ctx, 1)
    assert ctx.attacks == [mimic]


def test_find_next_step():
    floor = make_floor(OPEN)
    assert find_next_step(floor, (1, 1), (1, 1), lambda x, y: True, 100) is None
    assert find_next_step(floor, (1, 1), (4, 4), lambda x, y: True, 100) == Direction.DOWN_RIGHT
