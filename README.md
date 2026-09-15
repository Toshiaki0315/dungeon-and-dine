# Dungeon & Dine: 飢餓のトレジャーハンター（仮）

モンスターを調理して食いつなぐ、ターン制・8方向グリッドのローグライクRPG。Python + Pyxel 製。

- 開発仕様書: [docs/game_specification.md](docs/game_specification.md)
- コンセプト＆ストーリー: [docs/concept_story.md](docs/concept_story.md)
- 料理カットインの参考画像: `docs/cooking_cutin_concept.jpg`（権利確認が済むまで Git 管理外。必要な人にだけ個別に共有する）

## 動作環境

- Python 3.11 以上
- Pyxel 2.x（`pyxel>=2.0,<3`）
- Windows / macOS / Linux

## セットアップ

[uv](https://docs.astral.sh/uv/) を使う場合:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

pip を使う場合:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

日本語フォント（美咲ゴシック第2 BDF）を `assets/fonts/` に配置する。手順は [assets/fonts/README.md](assets/fonts/README.md) を参照。

## 起動

```bash
.venv/bin/python main.py
```

| 引数 | 内容 |
|---|---|
| `--seed <int>` | ランシードを固定する（同じダンジョンを再現） |
| `--scale <int>` | 表示倍率（既定 4） |
| `--debug` | 開発ビルド扱い（F1 でデバッグ表示） |

## テスト・Lint

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format .
```

## 操作方法

仕様書 3.2 を参照（実装に合わせて随時ここへ転記する）。

## 実装済み機能

- [x] 開発環境の準備（ディレクトリ構成、起動の雛形、データローダ、シード管理）
- [ ] フェーズ1: コア実装
- [ ] フェーズ2: ターン制とUI
- [ ] フェーズ3: 戦闘とインベントリ
- [ ] フェーズ4: 装備と呪い
- [ ] フェーズ5: 料理システム
- [ ] フェーズ6: 拠点・セーブ・メタ進行
- [ ] フェーズ7: ボス・演出・バランス調整

## 実装上の判断（仕様書 16章）

- 仕様書などの資料は `docs/` にまとめた。
- 仮素材の生成スクリプトは `tools/` に置く。
