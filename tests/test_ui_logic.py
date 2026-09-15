"""UI 層のうち、描画を伴わない計算部分のテスト。"""

from game.systems.message_log import MessageLog, highlight, strip_markup
from game.ui.command_bar import COMMANDS, CommandBar, button_rect, hit_test
from game.ui.hud import is_low
from game.ui.log import split_markup, wrap_text


def test_command_bar_has_six_commands_in_spec_order():
    assert [c.label for c in COMMANDS] == ["攻撃", "道具", "スキル", "料理", "装備", "地図"]


def test_hit_test_finds_button_under_mouse():
    for index in range(len(COMMANDS)):
        x, y, w, h = button_rect(index)
        assert hit_test(x + w // 2, y + h // 2) == index
    assert hit_test(0, 0) is None


def test_command_bar_selection_wraps_around():
    bar = CommandBar()
    bar.move(-1)
    assert bar.selected.id == "map"
    bar.move(1)
    assert bar.selected.id == "attack"


def test_wrap_text_by_pixel_width():
    assert wrap_text("abcdef", 8, lambda s: len(s) * 4) == ["ab", "cd", "ef"]
    assert wrap_text("", 8, lambda s: len(s) * 4) == [""]


def test_message_log_keeps_latest_100_entries():
    log = MessageLog()
    for i in range(105):
        log.add(f"message {i}")
    assert len(log) == 100
    assert log.entries[0] == "message 5"
    assert log.latest(2) == ["message 103", "message 104"]


def test_gauge_blinks_at_25_percent_or_less():
    assert is_low(25, 100)
    assert not is_low(26, 100)
    assert not is_low(0, 0)


def test_split_markup_carries_highlight_across_lines():
    line = f"レオは{highlight('薬草')}を拾った。"
    segments, highlighted = split_markup(line, False)
    assert segments == [("レオは", False), ("薬草", True), ("を拾った。", False)]
    assert not highlighted

    first, second = "長い" + "\x01アイテム", "名前\x02です"
    _, highlighted = split_markup(first, False)
    assert highlighted
    segments, highlighted = split_markup(second, highlighted)
    assert segments == [("名前", True), ("です", False)]


def test_wrap_ignores_markup_width():
    text = highlight("abcd") + "ef"
    lines = wrap_text(text, 16, lambda s: len(strip_markup(s)) * 4)
    assert [strip_markup(line) for line in lines] == ["abcd", "ef"]
