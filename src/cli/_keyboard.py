"""Keyboard CLI subcommands -- boot-keyboard (6KRO)."""

from __future__ import annotations

import argparse

from core.reports import ReportTable
from hid import Keyboard, Keycode

from ._common import output as _output, exit_fail as _exit

_KEY_CHOICES = sorted(k.name for k in Keycode if k.name != "NONE")

# -- ASCII → (shift-needed?, Keycode) mapping -------------------------------- #
# Maps printable ASCII characters to HID keycodes with shift flag.
# US keyboard layout assumed.

_ASCII_MAP: dict[str, tuple[bool, Keycode]] = {
    # lowercase letters (shift=False)
    "a": (False, Keycode.A), "b": (False, Keycode.B), "c": (False, Keycode.C),
    "d": (False, Keycode.D), "e": (False, Keycode.E), "f": (False, Keycode.F),
    "g": (False, Keycode.G), "h": (False, Keycode.H), "i": (False, Keycode.I),
    "j": (False, Keycode.J), "k": (False, Keycode.K), "l": (False, Keycode.L),
    "m": (False, Keycode.M), "n": (False, Keycode.N), "o": (False, Keycode.O),
    "p": (False, Keycode.P), "q": (False, Keycode.Q), "r": (False, Keycode.R),
    "s": (False, Keycode.S), "t": (False, Keycode.T), "u": (False, Keycode.U),
    "v": (False, Keycode.V), "w": (False, Keycode.W), "x": (False, Keycode.X),
    "y": (False, Keycode.Y), "z": (False, Keycode.Z),
    # uppercase letters (shift=True)
    "A": (True, Keycode.A), "B": (True, Keycode.B), "C": (True, Keycode.C),
    "D": (True, Keycode.D), "E": (True, Keycode.E), "F": (True, Keycode.F),
    "G": (True, Keycode.G), "H": (True, Keycode.H), "I": (True, Keycode.I),
    "J": (True, Keycode.J), "K": (True, Keycode.K), "L": (True, Keycode.L),
    "M": (True, Keycode.M), "N": (True, Keycode.N), "O": (True, Keycode.O),
    "P": (True, Keycode.P), "Q": (True, Keycode.Q), "R": (True, Keycode.R),
    "S": (True, Keycode.S), "T": (True, Keycode.T), "U": (True, Keycode.U),
    "V": (True, Keycode.V), "W": (True, Keycode.W), "X": (True, Keycode.X),
    "Y": (True, Keycode.Y), "Z": (True, Keycode.Z),
    # digits
    "0": (False, Keycode.ZERO), "1": (False, Keycode.ONE),
    "2": (False, Keycode.TWO), "3": (False, Keycode.THREE),
    "4": (False, Keycode.FOUR), "5": (False, Keycode.FIVE),
    "6": (False, Keycode.SIX), "7": (False, Keycode.SEVEN),
    "8": (False, Keycode.EIGHT), "9": (False, Keycode.NINE),
    # whitespace
    " ": (False, Keycode.SPACEBAR), "\n": (False, Keycode.RETURN),
    "\t": (False, Keycode.TAB),
    # shifted punctuation
    "!": (True, Keycode.ONE), "@": (True, Keycode.TWO),
    "#": (True, Keycode.THREE), "$": (True, Keycode.FOUR),
    "%": (True, Keycode.FIVE), "^": (True, Keycode.SIX),
    "&": (True, Keycode.SEVEN), "*": (True, Keycode.EIGHT),
    "(": (True, Keycode.NINE), ")": (True, Keycode.ZERO),
    "_": (True, Keycode.MINUS), "+": (True, Keycode.EQUAL),
    "{": (True, Keycode.LEFT_BRACKET), "}": (True, Keycode.RIGHT_BRACKET),
    "|": (True, Keycode.BACKSLASH),
    ":": (True, Keycode.SEMICOLON), '"': (True, Keycode.APOSTROPHE),
    "~": (True, Keycode.GRAVE),
    "<": (True, Keycode.COMMA), ">": (True, Keycode.PERIOD),
    "?": (True, Keycode.SLASH),
    # unshifted punctuation
    "-": (False, Keycode.MINUS), "=": (False, Keycode.EQUAL),
    "[": (False, Keycode.LEFT_BRACKET), "]": (False, Keycode.RIGHT_BRACKET),
    "\\": (False, Keycode.BACKSLASH),
    ";": (False, Keycode.SEMICOLON), "'": (False, Keycode.APOSTROPHE),
    "`": (False, Keycode.GRAVE),
    ",": (False, Keycode.COMMA), ".": (False, Keycode.PERIOD),
    "/": (False, Keycode.SLASH),
}


def _type_text(kb: Keyboard, text: str) -> int:
    """Send ASCII *text* as sequential keystrokes. Returns the number of
    characters successfully typed.  Unsupported characters are skipped with a
    warning to stderr."""
    count = 0
    for ch in text:
        entry = _ASCII_MAP.get(ch)
        if entry is None:
            print(f"warning: skipping unsupported character {ch!r}", file=__import__("sys").stderr)
            continue
        shift, kc = entry
        if shift:
            kb.press(Keycode.LEFT_SHIFT)
            kb.tap(kc)
            kb.release(Keycode.LEFT_SHIFT)
        else:
            kb.tap(kc)
        count += 1
    return count


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

    # type (ASCII text → keystrokes)
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
        count = _type_text(kb, args.text)
        _output({"action": "type", "text": args.text, "typed": count}, args.json)

    elif args.action == "release-all":
        kb.release_all()
        _output({"action": "release-all"}, args.json)
