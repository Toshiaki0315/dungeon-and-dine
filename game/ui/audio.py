"""効果音と BGM。仕様書 14章。

data/sounds.json の定義を Pyxel のサウンド／ミュージックに読み込み、名前で再生する。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pyxel

from game.data_loader import DataValidationError

SE_CHANNEL = 0  # 効果音を鳴らすチャンネル
BGM_CHANNELS = (1, 2)  # BGM に使うチャンネル


class Audio:
    def __init__(self, data: Mapping[str, Any]) -> None:
        self._se: dict[str, int] = {}
        self._bgm: dict[str, int] = {}
        self._current_bgm: str | None = None
        self._load(data)

    def _load(self, data: Mapping[str, Any]) -> None:
        index = 0
        for name, sound in data["se"].items():
            _set_sound(index, sound)
            self._se[name] = index
            index += 1

        for music_index, (name, bgm) in enumerate(data["bgm"].items()):
            if music_index >= len(pyxel.musics):
                raise DataValidationError("sounds.json: BGM の数が多すぎます")
            sequences: list[list[int]] = []
            for channel in bgm["channels"][: len(BGM_CHANNELS)]:
                _set_sound(index, {**channel, "speed": bgm["speed"]})
                sequences.append([index])
                index += 1
            while len(sequences) < len(BGM_CHANNELS):
                sequences.append([])
            pyxel.musics[music_index].set([], *sequences)
            self._bgm[name] = music_index

    def play_se(self, name: str) -> None:
        sound = self._se.get(name)
        if sound is not None:
            pyxel.play(SE_CHANNEL, sound)

    def play_bgm(self, name: str) -> None:
        """BGM を切り替える。同じ曲ならそのまま流し続ける。"""
        music = self._bgm.get(name)
        if music is None or name == self._current_bgm:
            return
        self._current_bgm = name
        pyxel.playm(music, loop=True)

    def stop_bgm(self) -> None:
        self._current_bgm = None
        for channel in BGM_CHANNELS:
            pyxel.stop(channel)


def _set_sound(index: int, sound: Mapping[str, Any]) -> None:
    if index >= len(pyxel.sounds):
        raise DataValidationError("sounds.json: 音の数が多すぎます")
    pyxel.sounds[index].set(
        str(sound["notes"]),
        str(sound["tones"]),
        str(sound["volumes"]),
        str(sound["effects"]),
        int(sound["speed"]),
    )
