"""ランキング（到達した階層・獲得した所持金）のテスト。仕様書 6.6。"""

from game.systems.meta import (
    OUTCOME_CLEAR,
    OUTCOME_DEATH,
    SCORE_CAPACITY,
    ScoreEntry,
    ranking_by_floor,
    ranking_by_gold,
)
from tests.test_meta import SLOTS, new_meta


def finish(meta, *, floor, gold, turn=100, survived=False, cleared=False):
    meta.finish_run(
        survived=survived,
        items=[],
        equipment=dict.fromkeys(SLOTS),
        gold=gold,
        floor_number=floor,
        turn=turn,
        cleared=cleared,
    )


def test_every_run_is_recorded_with_its_result():
    meta = new_meta()
    finish(meta, floor=7, gold=320, turn=540)
    assert len(meta.scores) == 1
    entry = meta.scores[0]
    assert (entry.name, entry.floor, entry.gold, entry.turn) == (meta.player_name, 7, 320, 540)
    assert entry.outcome == OUTCOME_DEATH and entry.outcome_label == "力尽きた"


def test_clearing_is_recorded_as_a_clear():
    meta = new_meta()
    finish(meta, floor=20, gold=900, survived=True, cleared=True)
    assert meta.scores[-1].outcome == OUTCOME_CLEAR


def test_ranking_by_floor_is_deepest_first_then_fastest():
    meta = new_meta()
    finish(meta, floor=5, gold=10, turn=300)
    finish(meta, floor=12, gold=20, turn=900)
    finish(meta, floor=12, gold=30, turn=400)  # 同じ階層ならターンが少ないほうが上
    ranking = ranking_by_floor(meta.scores)
    assert [(e.floor, e.turn) for e in ranking] == [(12, 400), (12, 900), (5, 300)]


def test_ranking_by_gold_is_richest_first():
    meta = new_meta()
    finish(meta, floor=3, gold=1500)
    finish(meta, floor=15, gold=200)
    finish(meta, floor=9, gold=780)
    assert [e.gold for e in ranking_by_gold(meta.scores)] == [1500, 780, 200]


def test_ranking_shows_at_most_the_requested_number():
    meta = new_meta()
    for floor in range(1, 16):
        finish(meta, floor=floor, gold=floor * 10)
    assert len(ranking_by_floor(meta.scores)) == 10
    assert len(ranking_by_gold(meta.scores, 3)) == 3


def test_old_records_are_dropped():
    meta = new_meta()
    for turn in range(SCORE_CAPACITY + 5):
        finish(meta, floor=2, gold=1, turn=turn)
    assert len(meta.scores) == SCORE_CAPACITY
    assert meta.scores[0].turn == 5  # 古いものから捨てる


def test_entries_keep_the_name_used_at_the_time():
    meta = new_meta()
    meta.player_name = "アリス"
    finish(meta, floor=4, gold=50)
    meta.player_name = "ボブ"
    finish(meta, floor=6, gold=70)
    assert [e.name for e in meta.scores] == ["アリス", "ボブ"]


def test_score_entry_labels():
    entry = ScoreEntry("レオ", 8, 120, 400, OUTCOME_DEATH)
    assert entry.outcome_label == "力尽きた"
