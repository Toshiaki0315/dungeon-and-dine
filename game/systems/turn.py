"""ターンスケジューラ（速度システム）。仕様書 5.1。

pyxel を import しないこと。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

ACTION_COST = 100  # 1回行動するのに必要なエネルギー
NORMAL_SPEED = 100  # 通常=100、倍速=200、鈍足=50


class Actor(Protocol):
    speed: int
    energy: int


@dataclass
class TurnScheduler:
    turn: int = 0

    def after_player_action(
        self,
        player: Actor,
        monsters: Sequence[Actor],
        act: Callable[[Actor], None],
        end_turn: Callable[[int], None],
        stop: Callable[[], bool] = lambda: False,
    ) -> None:
        """プレイヤーの1アクションのあと、プレイヤーが次に行動できるまで時間を進める。

        モンスターは生成順に、エネルギーが足りるだけ行動する。ターンの終わりに end_turn を呼び、
        全員に速度ぶんのエネルギーを加える。stop が True を返したら（死亡など）そこで止める。
        """
        player.energy -= ACTION_COST
        while player.energy < ACTION_COST:
            for monster in list(monsters):
                while monster.energy >= ACTION_COST:
                    monster.energy -= ACTION_COST
                    act(monster)
            self.turn += 1
            end_turn(self.turn)
            if stop():
                return
            player.energy += player.speed
            for monster in monsters:
                monster.energy += monster.speed
