# magichid-py

A Python client (the **"brain"**) for the [MagicHID](../magichid) transparent USB-HID
bridge. The ESP32-S3 firmware is a dumb relay — all protocol logic lives here.

* **sans-I/O core** — pure state machine, no threads, no serial dependency.
  Same core serves blocking and (future) asyncio edges.
* Wire codec verified **byte-for-byte** against `spec/protocol_vectors.txt`.
* Full session: handshake, reliable delivery (SEQ + ACK, retransmit-same-SEQ,
  dedup window), fire-and-forget, `HOST_EVENT` callbacks, identity switch.
* Report helpers for the `universal` (keyboard/mouse/…) and `horipad` (Switch) profiles,
  with machine-enforced **relative-reports-must-be-reliable** via the `RELATIVE` flag.

## Install

```bash
uv sync            # or: pip install -e ".[dev]"
```

Runtime dependency: `pyserial`. The contract lives in `spec/` (treat as read-only truth);
see [`spec/PROTOCOL.md`](spec/PROTOCOL.md).

## Quickstart

```python
from magichid.io.blocking import BlockingClient
from magichid.reports import KEYBOARD, keyboard_report, char_to_keycode

with BlockingClient("COM5") as c:
    c.handshake(timeout=10)    # PING until STATUS(MOUNTED|READY); asserts proto==2
    mod, key = char_to_keycode("a")
    c.request(0x01, bytes([KEYBOARD]) + keyboard_report([key], modifier=mod))
    # release automatically on exit (RELEASE_ALL)
```

Run the bundled demo:

```bash
python examples/hello_keyboard.py --port COM5 --char a
```

## Tests

```bash
pytest        # 60 tests: vectors + connection + io + reports
```

## Architecture

```
src/magichid/
  codec.py        CRC-16/CCITT-FALSE + COBS + build/parse_frame (vectors-locked)
  wire.py         Protocol constants (spec/protocol.yaml → code)
  events.py       Typed events the core emits (never silent drops)
  connection.py   Pure sans-I/O state machine (clock-injected, testable)
  io/blocking.py  Thin single-threaded edge over pyserial
  reports.py      ReportTable (CAPS+reports.json) + keyboard/mouse/horipad builders
```
