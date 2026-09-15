import json

import pytest

from game import data_loader


def test_all_data_files_load():
    data = data_loader.load_all()
    assert set(data) == {name.removesuffix(".json") for name in data_loader.REQUIRED_KEYS}


def test_missing_required_key_raises(tmp_path):
    for filename, required in data_loader.REQUIRED_KEYS.items():
        (tmp_path / filename).write_text(
            json.dumps({key: [] for key in required}), encoding="utf-8"
        )
    (tmp_path / "enemies.json").write_text(json.dumps({"version": 1}), encoding="utf-8")

    with pytest.raises(data_loader.DataValidationError, match="enemies"):
        data_loader.load_all(tmp_path)
