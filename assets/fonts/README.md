# フォント

このフォルダに **美咲ゴシック第2（8×8 px、BDF版）** を配置する（仕様書 2.5）。

| ファイル | 内容 |
|---|---|
| `misaki_gothic_2nd.bdf` | フォント本体（`game/config.py` の `FONT_PATH` で参照） |
| `LICENSE` | 配布元のライセンス文書 |

- 配布元: 美咲フォント（Little Limit）— https://littlelimit.net/misaki.htm
- 取得元: https://littlelimit.net/arc/misaki/misaki_bdf_2021-05-05.zip（2021-05-05 版）
  - `misaki_gothic_2nd.bdf` をそのまま配置し、同梱の `misaki.txt` を `LICENSE` として配置する。
- ライセンス（2026-09-16 確認）: フリーソフトウェア。改変の有無・商用非商用を問わず、使用・複製・再配布が自由（無保証）。
- 現在は、このフォルダの README 以外を `.gitignore` で Git 管理から除外している。clone した環境では各自で配置すること。
- 未配置の場合、ゲームは Pyxel の組み込みフォント（英数字のみ）で起動する。
