"""シーン（画面遷移の単位）。仕様書 4章。"""

from __future__ import annotations

from typing import Protocol


class Scene(Protocol):
    """各シーンが実装するインターフェース。

    `update` は次に遷移するシーンを返す（遷移しないときは None）。
    """

    def update(self) -> Scene | None: ...

    def draw(self) -> None: ...
