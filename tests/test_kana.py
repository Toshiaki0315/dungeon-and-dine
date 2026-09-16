"""名前入力の五十音表のテスト。仕様書 6.1。"""

import pytest

from game.ui import kana


def test_every_page_is_the_same_shape():
    for _, grid in kana.PAGES:
        assert len(grid) == 6
        assert {len(row) for row in grid} == {10}


def test_pages_have_the_expected_kana():
    hiragana = "".join("".join(row) for row in kana.HIRAGANA)
    katakana = "".join("".join(row) for row in kana.KATAKANA)
    for char in "あいうえおをんゃゅょっー":
        assert char in hiragana
    for char in "アイウエオヲンャュョッー":
        assert char in katakana
    assert len(hiragana) == len(katakana)


def test_empty_cells_are_reported_as_empty():
    grid = (tuple("あい　　　　　　　　"),)
    assert kana.char_at(grid, 0, 0) == "あ"
    assert kana.char_at(grid, 0, 2) == ""  # 全角空白は空欄
    assert kana.char_at(grid, 5, 0) == ""  # 表の外


def test_cursor_wraps_around_the_edges():
    grid = kana.HIRAGANA
    assert kana.move(grid, 0, 0, -1, 0) == (0, 9)  # 左端から右端へ
    assert kana.move(grid, 0, 9, 1, 0) == (0, 0)
    assert kana.move(grid, 0, 3, 0, -1) == (5, 3)  # 上端から下端へ
    assert kana.move(grid, 5, 3, 0, 1) == (0, 3)


@pytest.mark.parametrize(
    ("char", "expected"),
    [("か", "が"), ("し", "じ"), ("は", "ば"), ("カ", "ガ"), ("ホ", "ボ")],
)
def test_voiced_marks(char, expected):
    assert kana.voiced(char) == expected


@pytest.mark.parametrize(("char", "expected"), [("は", "ぱ"), ("ふ", "ぷ"), ("ヘ", "ペ")])
def test_semi_voiced_marks(char, expected):
    assert kana.semi_voiced(char) == expected


def test_marks_cannot_be_applied_to_every_character():
    assert kana.voiced("あ") is None
    assert kana.semi_voiced("か") is None


def test_apply_mark_changes_only_the_last_character():
    assert kana.apply_mark("さか") == "さが"
    assert kana.apply_mark("さは", semi=True) == "さぱ"
    assert kana.apply_mark("さあ") == "さあ"  # 付けられない文字はそのまま
    assert kana.apply_mark("") == ""


def test_page_names_and_grids_match():
    assert kana.page_name(0) == kana.PAGE_HIRAGANA
    assert kana.grid_for(1) is kana.KATAKANA
    assert kana.page_name(len(kana.PAGES)) == kana.PAGE_HIRAGANA  # 回り込む
