"""配布用の実行ファイルを作るスクリプト。

    .venv/bin/python tools/build.py

PyInstaller で、実行した OS 向けの実行ファイルを `dist/` に作る。
（PyInstaller は他の OS 向けの実行ファイルを作れないため、3 OS 分は
 .github/workflows/build.yml で各 OS のランナーが実行する）
ゲーム本体からは import しないこと。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "DungeonAndDine"
# 実行ファイルに同梱するフォルダ（ゲームは config.py 経由で参照する）
BUNDLED = ("assets", "data")


def _use_utf8_output() -> None:
    """標準出力を UTF-8 にする。

    Windows では標準出力が cp1252 などになることがあり、日本語のメッセージを
    print しただけで UnicodeEncodeError になってビルドが止まる。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _use_utf8_output()
    if shutil.which("pyinstaller") is None and not _module_available():
        print(
            "PyInstaller が見つかりません。次のコマンドで入れてください:\n"
            "  uv pip install --python .venv/bin/python pyinstaller",
            file=sys.stderr,
        )
        return 1

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
    ]
    for folder in BUNDLED:
        command += ["--add-data", f"{ROOT_DIR / folder}{os.pathsep}{folder}"]
    command.append(str(ROOT_DIR / "main.py"))

    print("実行:", " ".join(command))
    result = subprocess.run(command, cwd=ROOT_DIR, check=False)
    if result.returncode == 0:
        print(f"\ndist/ に {APP_NAME} を作りました（{sys.platform} 向け）")
    return result.returncode


def _module_available() -> bool:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        return False
    return True


if __name__ == "__main__":
    sys.exit(main())
