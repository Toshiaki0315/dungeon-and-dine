#!/usr/bin/env bash
# 手元でテストプレイするための起動スクリプト（macOS / Linux）。
# 使い方:
#   ./run.sh                  そのまま起動する
#   ./run.sh --seed 123       起動引数はそのまま main.py に渡す
#   ./run.sh --scale 2 --debug
set -euo pipefail

cd "$(dirname "$0")"

PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "仮想環境が見つかりません。先にセットアップしてください:"
  echo "  uv venv --python 3.11 .venv"
  echo "  uv pip install --python .venv/bin/python -r requirements.txt"
  exit 1
fi

exec "$PYTHON" main.py "$@"
