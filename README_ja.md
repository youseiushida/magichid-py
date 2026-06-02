# magichid-py

[MagicHID](../magichid) 透過 USB-HID ブリッジの Python クライアント（**「頭脳」**）。
ESP32-S3 ファームウェアは単純な中継器であり、プロトコルロジックは全てここにあります。

* **sans-I/O コア** — 純粋な状態機械。スレッド・シリアル依存ゼロ。
  同じコアの上に blocking エッジと（将来の）asyncio エッジが載ります。
* ワイヤコーデックは `spec/protocol_vectors.txt` に対して**バイト単位で検証**済み。
* 完全なセッション機能: ハンドシェイク、信頼配信（SEQ + ACK、同一SEQ再送、
  dedup ウィンドウ）、fire-and-forget、`HOST_EVENT` コールバック、識別子切り替え。
* `universal`（キーボード/マウス/…）と `horipad`（Nintendo Switch）の両プロファイル向け
  レポートヘルパー。`RELATIVE` フラグによる「相対レポートは信頼必須」ルールの
  **機械的強制**に対応。

## インストール

```bash
uv sync            # または: pip install -e ".[dev]"
```

実行時依存: `pyserial`。プロトコル仕様は `spec/` ディレクトリにあります（読み取り専用の真実として扱ってください）。
詳細は [`spec/PROTOCOL.md`](spec/PROTOCOL.md) を参照。

## クイックスタート

```python
from magichid.io.blocking import BlockingClient
from magichid.reports import KEYBOARD, keyboard_report, char_to_keycode

with BlockingClient("COM5") as c:
    c.handshake(timeout=10)    # PING を送り STATUS(MOUNTED|READY) を待つ。proto==2 を検証
    mod, key = char_to_keycode("a")
    c.request(0x01, bytes([KEYBOARD]) + keyboard_report([key], modifier=mod))
    # with ブロック終了時に自動で RELEASE_ALL
```

同梱のデモを実行:

```bash
python examples/hello_keyboard.py --port COM5 --char a
```

## テスト

```bash
pytest        # 60 テスト: vectors + connection + io + reports
```

## アーキテクチャ

```
src/magichid/
  codec.py        CRC-16/CCITT-FALSE + COBS + build/parse_frame（vectorsでロック）
  wire.py         プロトコル定数（spec/protocol.yaml → コード）
  events.py       コアが発行する型付きイベント（沈黙ドロップなし）
  connection.py   純粋 sans-I/O 状態機械（clock注入、テスト可能）
  io/blocking.py  薄い単一スレッドの pyserial エッジ
  reports.py      ReportTable（CAPS+reports.json）+ keyboard/mouse/horipad ビルダー
```

## プロトコルバージョン

このクライアントはファームウェア **プロトコルバージョン 2** を対象とします。
ハンドシェイク時に `STATUS` の `proto_version` バイトを検証し、不一致なら
`ProtocolVersionError` を送出します。

### spec v2 の主な特徴

- **CAPS エントリが 5 バイト化**（`[id][in_len][out_len][feat_len][flags]`）。
  `flags` の bit0 が `RELATIVE` フラグで、相対フィールドを含むレポートを表明します。
- **相対レポートは信頼モード必須**。`ReportTable` がこのルールを機械的に強制します。
- **`SET_IDENTITY` は ACK 待ち**。デバイスは ACK 送信後に再起動するため、
  オペレータは ACK を確認してからシリアルポートを再接続します。
- **dedup ウィンドウ = 16**。デバイスは適用済み SEQ を直近 16 個記憶し、
  重複を再 ACK するが再適用しません。クライアントは未 ACK の送信を 16 未満に保ちます。
- **`PING` と `STATUS` は相関しない**。`STATUS` はスナップショットです。
  `PING` をポーリングし、最新の `STATUS` で `MOUNTED|READY` を判定します。
- **デバイス→オペレータ通知（`HOST_EVENT`, `LOG`）はベストエフォート**。
  ACK も配送保証もありません。オペレータが FEATURE 状態の信頼できる情報源です。

## ライセンス

同梱の [LICENSE](LICENSE) ファイルを参照してください。
