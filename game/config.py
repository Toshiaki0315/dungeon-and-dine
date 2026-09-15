"""定数（画面サイズ、パス、キー割り当て等）。仕様書 2.3 / 3.2。

pyxel に依存しない値だけを置く。キーコードは pyxel 側の定数名（文字列）で持ち、
UI 層で `getattr(pyxel, name)` に変換して使う。
"""

from __future__ import annotations

from pathlib import Path

# --- パス（カレントディレクトリに依存しない） ---
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
ASSETS_DIR: Path = ROOT_DIR / "assets"
DATA_DIR: Path = ROOT_DIR / "data"
FONT_PATH: Path = ASSETS_DIR / "fonts" / "misaki_gothic_2nd.bdf"
RESOURCE_PATH: Path = ASSETS_DIR / "resources.pyxres"
CUTIN_DIR: Path = ASSETS_DIR / "cutins"

# --- アプリ ---
TITLE: str = "Dungeon & Dine"
APP_ID: str = "dungeon-and-dine"  # pyxel.user_data_dir(APP_ID, APP_ID)

# --- 画面 ---
SCREEN_WIDTH: int = 320
SCREEN_HEIGHT: int = 180
DISPLAY_SCALE: int = 4
FPS: int = 30

TILE_SIZE: int = 8
BOSS_TILE_SIZE: int = 16

STATUS_BAR_HEIGHT: int = 20
MAP_VIEW_HEIGHT: int = 120
BOTTOM_PANEL_HEIGHT: int = 40
MAP_VIEW_TILES_W: int = SCREEN_WIDTH // TILE_SIZE  # 40
MAP_VIEW_TILES_H: int = MAP_VIEW_HEIGHT // TILE_SIZE  # 15

LINE_HEIGHT: int = 10
TRANSPARENT_COLOR: int = 0

# --- キー割り当て（仕様書 3.2） ---
KEY_BINDINGS: dict[str, tuple[str, ...]] = {
    "up": ("KEY_UP", "KEY_W", "GAMEPAD1_BUTTON_DPAD_UP"),
    "down": ("KEY_DOWN", "KEY_S", "GAMEPAD1_BUTTON_DPAD_DOWN"),
    "left": ("KEY_LEFT", "KEY_A", "GAMEPAD1_BUTTON_DPAD_LEFT"),
    "right": ("KEY_RIGHT", "KEY_D", "GAMEPAD1_BUTTON_DPAD_RIGHT"),
    "up_left": ("KEY_KP_7",),
    "up_right": ("KEY_KP_9",),
    "down_left": ("KEY_KP_1",),
    "down_right": ("KEY_KP_3",),
    "confirm": ("KEY_SPACE", "KEY_RETURN", "GAMEPAD1_BUTTON_A"),
    "cancel": ("KEY_ESCAPE", "KEY_X", "GAMEPAD1_BUTTON_B"),
    "command_bar": ("KEY_TAB", "GAMEPAD1_BUTTON_X"),
    "inventory": ("KEY_I",),
    "skills": ("KEY_K",),
    "cook": ("KEY_C",),
    "equipment": ("KEY_E",),
    "map": ("KEY_M",),
    "notebook": ("KEY_R", "GAMEPAD1_BUTTON_Y"),
    "wait": ("KEY_PERIOD", "KEY_KP_5"),
    "log_history": ("KEY_L", "GAMEPAD1_BUTTON_BACK"),
    "debug": ("KEY_F1",),
}
