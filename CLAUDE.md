# CLAUDE.md

## プロジェクト概要

『Dungeon & Dine: 飢餓のトレジャーハンター（仮）』。モンスターを調理して食いつなぐ、ターン制・8方向グリッドのローグライクRPG（Pyxel 製）。

- **実装の正は [docs/game_specification.md](docs/game_specification.md)**。世界観は [docs/concept_story.md](docs/concept_story.md)（食い違ったら仕様書を優先）。
- 開発は仕様書 15章のフェーズ順に進める。各フェーズの DoD をすべて満たすまで次に進まない。

## 技術スタック

- 言語: Python 3.11 以上（venv は 3.11）
- フレームワーク: Pyxel 2.x（`pyxel>=2.0,<3`）
- テスト / Lint: pytest / ruff
- パッケージ管理: uv（`.venv/`）

## よく使うコマンド

- セットアップ: `uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -r requirements.txt`
- 起動: `.venv/bin/python main.py`（`--seed 123` でマップ再現、`--scale 2` で縮小表示）
- 手元でのテストプレイ: `./run.sh`（macOS / Linux。Finder からは `run.command`。Windows は `run.bat`）
- テスト: `.venv/bin/pytest`
- Lint / フォーマット: `.venv/bin/ruff check .` / `.venv/bin/ruff format .`
- 仮素材の再生成: `.venv/bin/python tools/make_placeholder_sprites.py`（`resources.pyxres` と `data/sprites.json` を上書き）
- カットイン背景の生成: `.venv/bin/python tools/make_cutin_background.py`（`assets/cutins/cooking_moss.png` を上書き）
- 自動プレイでバランス確認: `.venv/bin/python tools/simulate.py --runs 20`（`--start-floor` / `--start-level` で終盤だけ試せる）
- 配布用ビルド: `.venv/bin/python tools/build.py`（PyInstaller。3 OS 分は `.github/workflows/build.yml` が各 OS で実行する）

## ディレクトリ構成

- `main.py` — エントリポイント（引数解析 → `game.app.App`）
- `game/app.py` — Pyxel 初期化、シーン管理
- `game/config.py` — 画面サイズ・パス・キー割り当て
- `game/rng.py` — ランシード／階層シード
- `game/data_loader.py` — `data/*.json` の読み込みと必須キー検証
- `game/scenes/` — タイトル、拠点、ダンジョン、ゲームオーバー、エンディング
- `game/world/` `game/entities/` `game/systems/` — **ロジック層（pyxel を import しない）**
  - `game/systems/game_state.py` — ラン中の状態とターン進行の入口。ロジックのテストはここを操作する
  - `game/systems/catalog.py` — `data/` の敵・アイテム・罠・状態異常・スキルを読み込み、相互参照を検証する
  - `game/entities/ai.py` — 敵AI。`GameState` を `AIContext` として受け取る
  - `game/systems/equipment.py` — 装備の生成（修正値・印・呪い）、装備による補正の合計、未鑑定を隠した説明文
  - `game/systems/cooking.py` — 食材の定義・ドロップ率・レシピ照合・レシピ手帳
  - `game/systems/meta.py` — 拠点のデータ（資金・倉庫・持ち物・拡張）と施設の処理、死亡・生還の引き継ぎ
  - `game/systems/save.py` — `meta.json` / `run.json` の保存・読み込み（保存先パスは引数で受け取る）
  - `game/ui/cooking_cutin.py` — 料理カットイン（ワイプ、パレットの入れ替えと復帰、演出）
  - `game/ui/audio.py` — SE と BGM（`data/sounds.json` を `pyxel.sounds` / `pyxel.musics` に読み込む）
  - `game/ui/effects.py` — ダメージ表示・被弾の点滅・画面の揺れ・レベルアップの光
  - `game/ui/ranking_view.py` — ランキング（到達した階層・獲得した所持金）
  - `game/scenes/name_input.py` — 主人公の名前の入力（五十音表）
  - `game/ui/kana.py` — 五十音表の定義とカーソル移動（pyxel 非依存）
- `tests/helpers.py` — テスト用マップの作成（`make_floor`）と、出目を固定する乱数（`FixedRng`）
- `game/scenes/dungeon.py` — 入力の解釈とサブモード管理、描画の呼び出しだけを行う
- `game/ui/` — 描画・入力（文字描画は必ず `ui/font.py` の `draw_text` 経由）
- `data/` — 敵・アイテム・レシピ・バランス値などの JSON
- `assets/` — フォント、`resources.pyxres`、料理カットイン背景
- `tools/` — 仮素材生成などのスクリプト（ゲーム本体から import しない）
- `tests/` — pytest（ロジック層のみ）
- `docs/` — 仕様書・コンセプト・参考画像

## コーディングの決まり

- 型ヒント必須、PEP 8 準拠（ruff の設定は `pyproject.toml`）。エンティティは `dataclass` 基本。
- コメント・docstring・ログ文言は日本語。
- `world/` `entities/` `systems/` では `pyxel` を import しない（`tests/test_architecture.py` で検証）。
- 乱数はグローバルな `random` 関数を使わず、`random.Random` インスタンスを引数で渡す。
- 【仮】の数値はコードに直書きせず `data/` の JSON に定義する。
- パスは `pathlib.Path`、起点は `Path(__file__).resolve().parent`。ファイル I/O は `encoding="utf-8"`。
- セーブ先は `pyxel.user_data_dir("dungeon-and-dine", "dungeon-and-dine")`。書き込みは一時ファイル → リネーム。
- フェーズを終えたら README の「実装済み機能」を更新する。判断した未確定事項は README に記録する。

## 注意点・してほしくないこと

- **マップやキャラクターを文字（`@` `#` など）で描画しない。** 仮素材でもドット絵で描く。
- `docs/cooking_cutin_concept.jpg` は雰囲気の参考のみ。ゲーム素材として使わない。
- 16色パレット以外の色を使わない（料理カットイン中のパレット入れ替えのみ例外）。
- 新しい依存ライブラリを追加する前に確認する。

## その他メモ

- 日本語フォント（美咲ゴシック第2 BDF）は `assets/fonts/misaki_gothic_2nd.bdf` に置く。未配置時は組み込みフォントで起動する。
