"""経験値・レベルアップ・満腹度・自然回復。仕様書 6.2〜6.4 / 6.7。

pyxel を import しないこと。
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from game.data_loader import dataclass_from_dict
from game.entities.player import Player
from game.systems.skills import SkillDef

PERCENT = 100


@dataclass(frozen=True)
class SurvivalParams:
    """満腹度と自然回復のパラメータ。balance.json の "survival" で定義する。"""

    satiety_decay_interval: int  # このターン数ごとに満腹度が1減る
    hunger_warning_threshold: int
    starvation_damage: int
    hp_regen_interval: int
    hp_regen_amount: int
    mp_regen_interval: int
    mp_regen_amount: int
    descend_mp_recover_ratio: float

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SurvivalParams:
        return dataclass_from_dict(cls, data, "survival")


@dataclass(frozen=True)
class ProgressionParams:
    """レベルアップのパラメータ。balance.json の "progression" で定義する。"""

    exp_base: float
    exp_exponent: float
    max_level: int
    hp_per_level: int
    mp_per_level: int
    atk_per_level: int
    def_per_odd_level: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ProgressionParams:
        return dataclass_from_dict(cls, data, "progression")


def exp_to_next_level(level: int, params: ProgressionParams) -> int:
    """次のレベルまでに必要な経験値 floor(exp_base × Lv^exp_exponent)。"""
    return math.floor(params.exp_base * level**params.exp_exponent)


def gain_exp(
    player: Player,
    amount: int,
    params: ProgressionParams,
    skills: Mapping[str, SkillDef],
) -> list[str]:
    """経験値を加え、レベルアップとスキル習得を処理してメッセージを返す。

    経験値はレベルアップのたびに必要量を差し引く（ステータスバーは「現在値/次のレベルまで」）。
    """
    messages: list[str] = []
    player.exp += amount
    while player.level < params.max_level:
        needed = exp_to_next_level(player.level, params)
        if player.exp < needed:
            break
        player.exp -= needed
        player.level += 1
        player.max_hp += params.hp_per_level
        player.hp += params.hp_per_level
        player.max_mp += params.mp_per_level
        player.mp += params.mp_per_level
        player.atk += params.atk_per_level
        if player.level % 2 == 1:
            player.defense += params.def_per_odd_level
        messages.append(f"{player.name}はレベル{player.level}になった！")
        for skill in sorted(skills.values(), key=lambda s: s.level):
            if skill.level == player.level and skill.id not in player.skills:
                player.skills.append(skill.id)
                messages.append(f"「{skill.name}」を覚えた！")
    return messages


def apply_turn_end(
    player: Player,
    turn: int,
    params: SurvivalParams,
    hunger_rate_percent: int = PERCENT,
    *,
    can_regen_hp: bool = True,
) -> list[str]:
    """ターン終了時の満腹度・飢餓・自然回復を適用し、ログに出すメッセージを返す。

    hunger_rate_percent は満腹度の減る速さ（呪い・装備で 80 や 200 になる）。
    can_regen_hp は毒などで HP の自然回復が止まっているときに False にする。
    """
    messages: list[str] = []
    before = player.satiety

    # 小数の誤差が出ないよう、% 単位の整数で蓄積する
    player.satiety_progress += hunger_rate_percent
    threshold = params.satiety_decay_interval * PERCENT
    while player.satiety_progress >= threshold:
        player.satiety_progress -= threshold
        player.satiety = max(0, player.satiety - 1)

    warning = params.hunger_warning_threshold
    if before > warning >= player.satiety > 0:
        messages.append(f"{player.name}はおなかが減ってきた。")
    if before > 0 == player.satiety:
        messages.append(f"{player.name}は飢えている！")

    if player.satiety == 0:
        player.hp = max(0, player.hp - params.starvation_damage)
        return messages

    if can_regen_hp and turn % params.hp_regen_interval == 0:
        player.hp = min(player.max_hp, player.hp + params.hp_regen_amount)
    if turn % params.mp_regen_interval == 0:
        player.mp = min(player.max_mp, player.mp + params.mp_regen_amount)
    return messages


def recover_mp_on_descend(player: Player, params: SurvivalParams) -> int:
    """階段を降りたときに最大MPの一定割合を回復し、回復量を返す。"""
    amount = min(
        math.floor(player.max_mp * params.descend_mp_recover_ratio), player.max_mp - player.mp
    )
    player.mp += amount
    return amount
