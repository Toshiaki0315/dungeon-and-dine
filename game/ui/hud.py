"""上部ステータスバー。仕様書 2.3 / 14章。"""

from __future__ import annotations

import math

import pyxel

from game import config
from game.entities.player import Player
from game.ui import font

COLOR_TEXT = 7
COLOR_LABEL = 13
COLOR_FRAME = 1
COLOR_GAUGE_BG = 1
COLOR_HP = 8  # 赤
COLOR_MP = 12  # 青
COLOR_SATIETY = 9  # 橙

GAUGE_W = 32
GAUGE_H = 5
LOW_RATIO = 0.25  # この割合以下で点滅する
BLINK_TICKS = 8

LINE1_Y = 1
LINE2_Y = 11


def is_low(value: int, maximum: int) -> bool:
    return maximum > 0 and value / maximum <= LOW_RATIO


def draw_status_bar(player: Player, floor_label: str, exp_next: int) -> None:
    font.draw_text(2, LINE1_Y, floor_label, COLOR_TEXT)
    font.draw_text(120, LINE1_Y, f"Lv{player.level}", COLOR_TEXT)
    font.draw_text(152, LINE1_Y, f"EXP {player.exp}/{exp_next}", COLOR_TEXT)
    gold = f"{player.gold}G"
    font.draw_text(config.SCREEN_WIDTH - 2 - font.text_width(gold), LINE1_Y, gold, COLOR_TEXT)

    _draw_stat(2, "HP", player.hp, player.max_hp, COLOR_HP, f"{player.hp}/{player.max_hp}")
    _draw_stat(108, "MP", player.mp, player.max_mp, COLOR_MP, f"{player.mp}/{player.max_mp}")
    _draw_stat(214, "満腹", player.satiety, player.max_satiety, COLOR_SATIETY, str(player.satiety))

    y = config.MAP_TOP - 1
    pyxel.line(0, y, config.SCREEN_WIDTH - 1, y, COLOR_FRAME)


def _draw_stat(x: int, label: str, value: int, maximum: int, color: int, text: str) -> None:
    font.draw_text(x, LINE2_Y, label, COLOR_LABEL)
    gauge_x = x + font.text_width(label) + 3
    draw_gauge(gauge_x, LINE2_Y + 1, value, maximum, color)
    font.draw_text(gauge_x + GAUGE_W + 3, LINE2_Y, text, COLOR_TEXT)


def draw_gauge(x: int, y: int, value: int, maximum: int, color: int) -> None:
    pyxel.rect(x, y, GAUGE_W, GAUGE_H, COLOR_GAUGE_BG)
    if is_low(value, maximum) and (pyxel.frame_count // BLINK_TICKS) % 2:
        return
    fill = math.ceil(GAUGE_W * value / maximum) if maximum > 0 and value > 0 else 0
    if fill > 0:
        pyxel.rect(x, y, min(fill, GAUGE_W), GAUGE_H, color)
