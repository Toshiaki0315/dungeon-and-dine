"""シード管理。仕様書 2.6。

グローバルな `random` モジュールの関数は使わず、`random.Random` のインスタンスを渡す。
"""

from __future__ import annotations

import random
import secrets


def new_run_seed() -> int:
    """新しい挑戦のランシードを生成する。"""
    return secrets.randbits(32)


def floor_seed(run_seed: int, floor: int) -> int:
    """階層のシードを `hash((run_seed, floor))` から導出する。

    int のタプルのハッシュは PYTHONHASHSEED の影響を受けないため、OS・実行間で再現できる。
    """
    return hash((run_seed, floor))


def floor_rng(run_seed: int, floor: int) -> random.Random:
    """階層用の乱数生成器を返す。"""
    return random.Random(floor_seed(run_seed, floor))
