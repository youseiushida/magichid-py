"""HORIPAD (Nintendo Switch) CLI subcommands."""

from __future__ import annotations

import argparse

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
