"""Unicode text input CLI subcommand."""

from __future__ import annotations

import argparse

from core.reports import ReportTable
from hid import UnicodeInput

from ._common import output as _output, exit_fail as _exit


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("unicode", help="Direct Unicode text input")
    p.add_argument("--text", required=True, help="Text to send as UTF-16LE code units")


def run(args: argparse.Namespace, client) -> None:
    table = ReportTable.universal()
    uni = UnicodeInput(client, table)
    uni.type(args.text)
    _output({"action": "type", "text": args.text, "length": len(args.text)}, args.json)
