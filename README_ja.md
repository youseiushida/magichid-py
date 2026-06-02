# magichid

[MagicHID](https://github.com/youseiushida/magichid) の Python クライアント。

## インストール

```
pip install magichid
```

## クイックスタート -- 高レベル API

```python
from core.io.blocking import BlockingClient
from core.reports import ReportTable
from hid import Keyboard, Keycode, Mouse, MouseButton, Digitizer

with BlockingClient("COM5") as c:
    c.handshake()

    # キーボード
    kb = Keyboard(c, ReportTable.universal())
    kb.tap(Keycode.A)
    kb.type_text("Hello world")

    # マウス
    mouse = Mouse(c, ReportTable.universal())
    mouse.move(x=10, y=-5)
    mouse.click(MouseButton.LEFT)

    # タッチパネル
    dig = Digitizer(c, ReportTable.universal())
    dig.down(x=0.5, y=0.5)
    dig.move(x=0.6, y=0.5)
    dig.up()
```

`hid.universal` には 35 のデバイスクラスがあります。キーボード、マウス、ゲームパッド、
フライトシム、VR ヘッドセット、ゴルフクラブ、コンシューマ制御、タッチパネル、ハプティクス、
フォースフィードバック、Unicode 入力、アイトラッカー、加速度センサー、医療用超音波、
点字ディスプレイ、LampArray、モニター制御、UPS、バッテリー、バーコードスキャナ、
秤、磁気ストライプリーダー、カメラ制御、アーケード I/O、ゲーミングデバイス、
FIDO 認証器など。

Horipad（Nintendo Switch、プロファイル 1）は `hid.horipad` にあります。

## クイックスタート -- CLI

```
magichid --port COM5 keyboard type --text "Hello world"
magichid --port COM5 mouse move --x 10 --y -5 --json
magichid --port COM5 digitizer down --x 0.5 --y 0.5
magichid --port COM5 unicode type --text "Hello (U+1F389)"
magichid --port COM5 horipad press --button A --json
magichid --port COM5 soc firmware-chunk --firmware-id 1 --offset 0 --payload-file chunk.bin

# エージェント向け自己記述
magichid agent-context | jq .commands.mouse.actions
```

CLI はデフォルトで非対話です。`--json` で構造化出力。エラーは stderr に有効値一覧付きで
出力されます。`agent-context` はバージョン付きの機械可読スキーマを提供します。
