"""HORIPAD (Nintendo Switch) CLI subcommands."""

from __future__ import annotations

import argparse
import time

from core.reports import ReportTable
from hid.horipad import Horipad, HoripadButton, HoripadDpad

from ._common import output as _output, exit_fail as _exit

_BUTTON_CHOICES = [b.name.lower() for b in HoripadButton]
_DPAD_CHOICES = [d.name.lower() for d in HoripadDpad]


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("horipad", help="HORIPAD Nintendo Switch controller")
    sub2 = p.add_subparsers(dest="action", required=True)

    # press
    pr = sub2.add_parser("press", help="Press (hold) a button")
    pr.add_argument("--button", action="append", required=True, dest="buttons",
                    choices=_BUTTON_CHOICES, metavar="BUTTON",
                    help=f"Button to hold (repeatable). Valid: {{{', '.join(_BUTTON_CHOICES)}}}")

    # hold
    h = sub2.add_parser("hold", help="Hold one or more buttons for a duration")
    h.add_argument("--button", action="append", required=True, dest="buttons",
                   choices=_BUTTON_CHOICES, metavar="BUTTON",
                   help=f"Button to hold (repeatable). Valid: {{{', '.join(_BUTTON_CHOICES)}}}")
    h.add_argument("--duration-ms", type=float, default=1000.0,
                   help="Hold duration in milliseconds (default: 1000)")
    h.add_argument("--interval-ms", type=float, default=100.0,
                   help="Refresh interval in milliseconds (default: 100; must be < watchdog)")

    # release
    r = sub2.add_parser("release", help="Release a held button")
    r.add_argument("--button", action="append", required=True, dest="buttons",
                   choices=_BUTTON_CHOICES, metavar="BUTTON",
                   help=f"Button to release (repeatable)")

    # tap
    t = sub2.add_parser("tap", help="Press and release a button immediately")
    t.add_argument("--button", action="append", required=True, dest="buttons",
                   choices=_BUTTON_CHOICES, metavar="BUTTON",
                   help=f"Button to tap (repeatable)")

    # dpad
    dp = sub2.add_parser("dpad", help="Set D-pad direction")
    dp.add_argument("--direction", required=True, choices=_DPAD_CHOICES,
                    help=f"D-pad direction {{{', '.join(_DPAD_CHOICES)}}}")

    # stick-left
    sl = sub2.add_parser("stick-left", help="Set left analog stick")
    sl.add_argument("--x", type=float, default=0.0, help="X axis (-1.0..1.0)")
    sl.add_argument("--y", type=float, default=0.0, help="Y axis (-1.0..1.0)")
    sl.add_argument("--raw", action="store_true", default=False,
                    help="Treat --x/--y as raw 0x00-0xFF values")

    # stick-right
    sr = sub2.add_parser("stick-right", help="Set right analog stick")
    sr.add_argument("--x", type=float, default=0.0, help="X axis (-1.0..1.0)")
    sr.add_argument("--y", type=float, default=0.0, help="Y axis (-1.0..1.0)")
    sr.add_argument("--raw", action="store_true", default=False,
                    help="Treat --x/--y as raw 0x00-0xFF values")

    # release-all
    sub2.add_parser("release-all", help="Release all buttons, centre sticks and dpad")


def run(args: argparse.Namespace, client) -> None:
    table = ReportTable.horipad()
    pad = Horipad(client, table)

    if args.action in ("press", "release", "tap"):
        buttons = [HoripadButton[b.upper()] for b in args.buttons]
        getattr(pad, args.action)(*buttons)
        _output({"action": args.action, "buttons": [b.name for b in buttons]}, args.json)

    elif args.action == "hold":
        if args.duration_ms < 0:
            _exit(2, "--duration-ms must be >= 0")
        if args.interval_ms <= 0:
            _exit(2, "--interval-ms must be > 0")
        buttons = [HoripadButton[b.upper()] for b in args.buttons]
        pad.release_all()
        time.sleep(0.1)
        pad.press(*buttons)
        _hold_for(pad, args.duration_ms, args.interval_ms)
        pad.release(*buttons)
        _output({
            "action": "hold",
            "buttons": [b.name for b in buttons],
            "duration_ms": args.duration_ms,
            "interval_ms": args.interval_ms,
        }, args.json)

    elif args.action == "dpad":
        direction = HoripadDpad[args.direction.upper()]
        pad.set_dpad(direction)
        _output({"action": "dpad", "direction": direction.name}, args.json)

    elif args.action == "stick-left":
        if args.raw:
            pad.set_stick_left_raw(x=int(args.x), y=int(args.y))
        else:
            pad.set_stick_left(x=args.x, y=args.y)
        _output({"action": "stick-left", "x": args.x, "y": args.y, "raw": args.raw}, args.json)

    elif args.action == "stick-right":
        if args.raw:
            pad.set_stick_right_raw(x=int(args.x), y=int(args.y))
        else:
            pad.set_stick_right(x=args.x, y=args.y)
        _output({"action": "stick-right", "x": args.x, "y": args.y, "raw": args.raw}, args.json)

    elif args.action == "release-all":
        pad.release_all()
        _output({"action": "release-all"}, args.json)


def _hold_for(pad: Horipad, duration_ms: float, interval_ms: float) -> None:
    remaining = duration_ms
    while remaining > 0:
        chunk = min(remaining, interval_ms)
        time.sleep(chunk / 1000.0)
        remaining -= chunk
        if remaining > 0:
            pad.resend()
