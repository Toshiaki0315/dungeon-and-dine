# フォント

**美咲ゴシック第2（8×8 px、BDF版）** をこのフォルダに同梱している（仕様書 2.5）。
再配布が許諾されているため、clone すればそのまま日本語が表示される。

| ファイル | 内容 |
|---|---|
| `misaki_gothic_2nd.bdf` | フォント本体（`game/config.py` の `FONT_PATH` で参照） |
| `LICENSE` | 配布元のライセンス文書 |

- 配布元: 美咲フォント（Little Limit）— https://littlelimit.net/misaki.htm
- 取得元: https://littlelimit.net/arc/misaki/misaki_bdf_2021-05-05.zip（2021-05-05 版）
  - `misaki_gothic_2nd.bdf` をそのまま配置し、同梱の `misaki.txt` を `LICENSE` として配置する。
- ライセンス（2026-09-16 確認）: フリーソフトウェア。改変の有無・商用非商用を問わず、使用・複製・再配布が自由（無保証）。
  原文は同梱の `LICENSE`（配布元の `misaki.txt`）を参照すること。
  > These fonts are free softwares.
  > Unlimited permission is granted to use, copy, and distribute it, with or without modification, either commercially and noncommercially.
  > THESE FONTS ARE PROVIDED "AS IS" WITHOUT WARRANTY.
- 差し替える場合は、フォント本体と一緒に配布元のライセンス文書も必ず添えること。
- フォント本体が無い場合、ゲームは Pyxel の組み込みフォント（英数字のみ）で起動する。
