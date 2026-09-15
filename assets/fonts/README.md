# フォント

このフォルダに **美咲ゴシック第2（8×8 px、BDF版）** を配置する（仕様書 2.5）。

| ファイル | 内容 |
|---|---|
| `misaki_gothic_2nd.bdf` | フォント本体（`game/config.py` の `FONT_PATH` で参照） |
| `LICENSE` | 配布元のライセンス文書 |

- 配布元: 美咲フォント（Little Limit）— https://littlelimit.net/misaki.htm
- 配布元のアーカイブに含まれる BDF ファイルを上記の名前で置き、ライセンス条件を確認のうえ文書を同梱すること。
- 再配布の条件を確認するまで、このフォルダの README 以外は `.gitignore` で Git 管理から除外している。clone した環境では各自で配置すること。
- 未配置の場合、ゲームは Pyxel の組み込みフォント（英数字のみ）で起動する。
