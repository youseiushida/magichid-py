"""Mouse CLI subcommands -- boot-mouse 5-byte relative report."""

from __future__ import annotations

import argparse

from core.reports import ReportTable
from hid import Mouse, MouseButton

from ._common import output as _output, exit_fail as _exit

_BUTTON_CHOICES = [b.name.lower() for b in MouseButton]


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("mouse", help="Boot-mouse (relative pointer)")
    sub2 = p.add_subparsers(dest="action", required=True)

    # move
    m = sub2.add_parser("move", help="Send relative movement deltas")
    m.add_argument("--x", type=int, default=0, help="X delta (-127..127)")
    m.add_argument("--y", type=int, default=0, help="Y delta (-127..127)")

    # scroll
    s = sub2.add_parser("scroll", help="Send scroll deltas")
    s.add_argument("--wheel", type=int, default=0, help="Vertical scroll (-127..127)")
    s.add_argument("--pan", type=int, default=0, help="Horizontal scroll (-127..127)")

    # click
    c = sub2.add_parser("click", help="Press and release a button")
    c.add_argument("--button", required=True, choices=_BUTTON_CHOICES,
                   help=f"Button to click {{{', '.join(_BUTTON_CHOICES)}}}")

    # press
    pr = sub2.add_parser("press", help="Press (hold) a button")
    pr.add_argument("--button", required=True, choices=_BUTTON_CHOICES,
                    help=f"Button to hold {{{', '.join(_BUTTON_CHOICES)}}}")

    # release
    r = sub2.add_parser("release", help="Release a held button")
    r.add_argument("--button", required=True, choices=_BUTTON_CHOICES,
                   help=f"Button to release {{{', '.join(_BUTTON_CHOICES)}}}")

    # release-all
    sub2.add_parser("release-all", help="Release all buttons")


def run(args: argparse.Namespace, client) -> None:
    table = ReportTable.universal()
    mouse = Mouse(client, table)

    if args.action == "move":
        mouse.move(x=args.x, y=args.y)
        _output({"action": "move", "x": args.x, "y": args.y}, args.json)

    elif args.action == "scroll":
        mouse.scroll(wheel=args.wheel, pan=args.pan)
        _output({"action": "scroll", "wheel": args.wheel, "pan": args.pan}, args.json)

    elif args.action == "click":
        btn = MouseButton[args.button.upper()]
        mouse.click(btn)
        _output({"action": "click", "button": btn.name}, args.json)

    elif args.action == "press":
        btn = MouseButton[args.button.upper()]
        mouse.press(btn)
        _output({"action": "press", "button": btn.name}, args.json)

    elif args.action == "release":
        btn = MouseButton[args.button.upper()]
        mouse.release(btn)
        _output({"action": "release", "button": btn.name}, args.json)

    elif args.action == "release-all":
        mouse.release_all()
        _output({"action": "release-all"}, args.json)
