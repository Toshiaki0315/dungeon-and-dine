import subprocess
import sys

from game import rng


def test_same_seed_and_floor_give_same_sequence():
    a = rng.floor_rng(12345, 3)
    b = rng.floor_rng(12345, 3)
    assert [a.random() for _ in range(10)] == [b.random() for _ in range(10)]


def test_different_floors_give_different_sequences():
    a = rng.floor_rng(12345, 3)
    b = rng.floor_rng(12345, 4)
    assert [a.random() for _ in range(10)] != [b.random() for _ in range(10)]


def test_floor_seed_is_stable_across_processes():
    """PYTHONHASHSEED が変わっても同じシードになること。"""
    code = "from game import rng; print(rng.floor_seed(12345, 3))"
    outputs = {
        subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONHASHSEED": hs, "PYTHONPATH": "."},
        ).stdout
        for hs in ("0", "1", "random")
    }
    assert len(outputs) == 1
