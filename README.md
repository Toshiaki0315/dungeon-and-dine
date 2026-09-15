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

## 仮素材の再生成

```bash
.venv/bin/python tools/make_placeholder_sprites.py
```

`assets/resources.pyxres` のイメージバンク0と `data/sprites.json` を上書きする。本素材に差し替えたあとは実行しないこと。

## 操作方法

実装済みの操作のみ（全体は仕様書 3.2）。

| 操作 | キーボード | ゲームパッド |
|---|---|---|
| 移動（上下左右） | 矢印キー / WASD | 十字キー |
| 斜め移動 | テンキー 7・9・1・3、または Shift を押しながら2方向同時押し | LB を押しながら十字キー |
| 向きだけ変える | Ctrl を押しながら方向キー | RB を押しながら十字キー |
| デバッグ表示（シード・座標） | F1（`--debug` 起動時のみ） | - |

押しっぱなしにすると 0.15 秒ごとに連続移動する（`data/balance.json` の `input.repeat_interval_sec`）。

## 実装済み機能

- [x] 開発環境の準備（ディレクトリ構成、起動の雛形、データローダ、シード管理）
- [x] フェーズ1: コア実装（※DoD「日本語の文字列が表示される」はフォント配置後に確認）
  - BSP法によるマップ生成（`--seed` で再現、全部屋の到達可能性をテストで検証）
  - `sprites.json` 経由のスプライト描画と仮素材（床・壁・通路・下り階段・レオ4方向×2コマ）
  - プレイヤー中心のカメラスクロール
  - 8方向移動、壁と角抜けの当たり判定
  - 階層到着時のバナー表示（B1F 苔むす洞窟）
- [ ] フェーズ2: ターン制とUI
- [ ] フェーズ3: 戦闘とインベントリ
- [ ] フェーズ4: 装備と呪い
- [ ] フェーズ5: 料理システム
- [ ] フェーズ6: 拠点・セーブ・メタ進行
- [ ] フェーズ7: ボス・演出・バランス調整

## 実装上の判断（仕様書 16章）

- 仕様書などの資料は `docs/` にまとめた。
- 仮素材の生成スクリプトは `tools/` に置く。
- 仕様書 2.8 の構成に加え、`world/direction.py`（8方向）、`ui/camera.py`（カメラ位置の計算）、`ui/input.py`（入力の解釈）を追加した。
- カメラはプレイヤーを中心にするが、マップの端ではマップ外が映らないように止める。
- 部屋や通路に接していない岩盤は描画せず黒のままにする（部屋と通路の輪郭だけ壁を描く）。
- BSP の分割区画・部屋サイズの上下限は `balance.json` の `mapgen` で定義する。兄弟区画の部屋どうしを、中心が最も近い組み合わせでL字の通路でつなぐ。
