"""Minimal end-to-end demo: type one character through the MagicHID bridge.

Flow (spec/PROTOCOL.md §6 recommended session)::

    open serial (1 Mbps) -> PING -> wait STATUS(MOUNTED|READY)
      -> SEND_REPORT(KEYBOARD, [mod, 0, key, 0,0,0,0,0])   # press
      -> brief hold -> release the key
      -> RELEASE_ALL (automatic on context exit)

Usage::

    python examples/hello_keyboard.py --port COM5             # Windows
    python examples/hello_keyboard.py --port /dev/ttyUSB0     # Linux/macOS
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _ROOT + "/src")

from core.events import HostEventReceived         # noqa: E402
from core.io.blocking import BlockingClient       # noqa: E402
from core.reports import KEYBOARD                 # noqa: E402
from examples._keyboard import char_to_keycode, keyboard_report  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Type one character via core.")
    ap.add_argument("--port", required=True, help="serial port (e.g. COM5)")
    ap.add_argument("--baud", type=int, default=1_000_000)
    ap.add_argument("--char", default="a", help="character to type")
    ap.add_argument("--hold", type=float, default=0.3, help="hold seconds")
    ap.add_argument("--timeout", type=float, default=10.0, help="handshake timeout")
    args = ap.parse_args(argv)

    modifier, keycode = char_to_keycode(args.char)

    with BlockingClient(args.port, baudrate=args.baud) as c:
        print(f"handshaking on {args.port} ...")
        s = c.handshake(timeout=args.timeout)
        print(f"ready: flags={s.flags:#04x} proto_version={s.proto_version}")

        caps = c.get_caps(timeout=2.0)
        print(f"profile: {len(caps.entries)} reports")

        print(f"typing {args.char!r} (keycode={keycode:#04x})")
        c.request(0x01, bytes([KEYBOARD]) + keyboard_report([keycode], modifier=modifier))
        time.sleep(args.hold)
        c.request(0x01, bytes([KEYBOARD]) + keyboard_report([]))

        for e in c.drain_events():
            if isinstance(e, HostEventReceived):
                print(f"[host-event] id={e.report_id} type={e.type_name} data={e.data.hex()}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
