"""Keyboard CLI subcommands -- boot-keyboard (6KRO)."""

from __future__ import annotations

import argparse

from core.reports import ReportTable
from hid import Keyboard, Keycode

from ._common import output as _output, exit_fail as _exit

_KEY_CHOICES = sorted(k.name for k in Keycode if k.name != "NONE")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("keyboard", help="Boot-keyboard (6KRO)")
    sub2 = p.add_subparsers(dest="action", required=True)

    # press
    pr = sub2.add_parser("press", help="Press (hold) one or more keys")
    pr.add_argument("--key", action="append", required=True, dest="keys",
                    choices=_KEY_CHOICES, metavar="KEY",
                    help=f"Key to press (repeatable)")

    # release
    r = sub2.add_parser("release", help="Release one or more keys")
    r.add_argument("--key", action="append", required=True, dest="keys",
                   choices=_KEY_CHOICES, metavar="KEY",
                   help=f"Key to release (repeatable)")

    # tap
    t = sub2.add_parser("tap", help="Press and release a key immediately")
    t.add_argument("--key", action="append", required=True, dest="keys",
                   choices=_KEY_CHOICES, metavar="KEY",
                   help=f"Key to tap (repeatable)")

    # type (delegates to Keyboard.type_text)
    ty = sub2.add_parser("type", help="Type an ASCII text string as keystrokes")
    ty.add_argument("--text", required=True, help="Text to type (ASCII, US keyboard layout)")

    # release-all
    sub2.add_parser("release-all", help="Release all held keys")


def run(args: argparse.Namespace, client) -> None:
    table = ReportTable.universal()
    kb = Keyboard(client, table)

    if args.action == "press":
        keys = [Keycode[k] for k in args.keys]
        kb.press(*keys)
        _output({"action": "press", "keys": [k.name for k in keys]}, args.json)

    elif args.action == "release":
        keys = [Keycode[k] for k in args.keys]
        kb.release(*keys)
        _output({"action": "release", "keys": [k.name for k in keys]}, args.json)

    elif args.action == "tap":
        keys = [Keycode[k] for k in args.keys]
        kb.tap(*keys)
        _output({"action": "tap", "keys": [k.name for k in keys]}, args.json)

    elif args.action == "type":
        count = kb.type_text(args.text)
        _output({"action": "type", "text": args.text, "typed": count}, args.json)

    elif args.action == "release-all":
        kb.release_all()
        _output({"action": "release-all"}, args.json)
