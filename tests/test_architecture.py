"""設計ルールの検証（仕様書 2.1: ロジック層では pyxel を import しない）。"""

import ast
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent / "game"
LOGIC_PACKAGES = ("world", "entities", "systems")
LOGIC_MODULES = ("config.py", "rng.py", "data_loader.py")


def _logic_files() -> list[Path]:
    files = [p for pkg in LOGIC_PACKAGES for p in (GAME_DIR / pkg).rglob("*.py")]
    files += [GAME_DIR / name for name in LOGIC_MODULES]
    return sorted(files)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("path", _logic_files(), ids=lambda p: str(p.relative_to(GAME_DIR)))
def test_logic_layer_does_not_import_pyxel(path: Path):
    assert "pyxel" not in _imported_modules(path)


def test_pyxel_text_is_called_only_in_font_module():
    """マップやキャラクターを文字で描かないよう、pyxel.text は ui/font.py だけで使う。"""
    offenders = []
    for path in sorted(GAME_DIR.rglob("*.py")):
        if path == GAME_DIR / "ui" / "font.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "text"
                and isinstance(node.value, ast.Name)
                and node.value.id == "pyxel"
            ):
                offenders.append(f"{path.relative_to(GAME_DIR)}:{node.lineno}")
    assert offenders == []


def test_key_binding_names_exist_in_pyxel():
    import pyxel

    from game import config

    missing = [n for names in config.KEY_BINDINGS.values() for n in names if not hasattr(pyxel, n)]
    assert missing == []


@pytest.mark.parametrize("path", _logic_files(), ids=lambda p: str(p.relative_to(GAME_DIR)))
def test_logic_layer_does_not_use_global_random(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "random":
            assert all(alias.name == "Random" for alias in node.names), (
                "random モジュールの関数は使わず random.Random を渡すこと（仕様書 2.6）"
            )
