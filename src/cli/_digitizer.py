"""Digitizer CLI subcommands -- absolute touch screen."""

from __future__ import annotations

import argparse

from core.reports import ReportTable
from hid import Digitizer

from ._common import output as _output, exit_fail as _exit


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("digitizer", help="Absolute-position touch digitizer")
    sub2 = p.add_subparsers(dest="action", required=True)

    # down
    d = sub2.add_parser("down", help="Touch down at position")
    d.add_argument("--x", type=float, required=True, help="X position (0.0-1.0)")
    d.add_argument("--y", type=float, required=True, help="Y position (0.0-1.0)")
    d.add_argument("--pressure", type=float, default=0.5,
                   help="Pressure (0.0-1.0, default: 0.5)")
    d.add_argument("--contact-id", type=int, default=0,
                   help="Contact identifier for multi-touch (0-255)")

    # move
    m = sub2.add_parser("move", help="Move contact while touching")
    m.add_argument("--x", type=float, required=True, help="X position (0.0-1.0)")
    m.add_argument("--y", type=float, required=True, help="Y position (0.0-1.0)")
    m.add_argument("--pressure", type=float, default=None,
                   help="Pressure (0.0-1.0). Omit to keep current pressure.")

    # up
    sub2.add_parser("up", help="Lift contact (touch up)")


def run(args: argparse.Namespace, client) -> None:
    table = ReportTable.universal()
    dig = Digitizer(client, table)

    if args.action == "down":
        dig.down(x=args.x, y=args.y, pressure=args.pressure,
                 contact_id=args.contact_id)
        _output({
            "action": "down", "x": args.x, "y": args.y,
            "pressure": args.pressure, "contact_id": args.contact_id,
        }, args.json)

    elif args.action == "move":
        dig.move(x=args.x, y=args.y, pressure=args.pressure)
        out = {"action": "move", "x": args.x, "y": args.y}
        if args.pressure is not None:
            out["pressure"] = args.pressure
        _output(out, args.json)

    elif args.action == "up":
        dig.up()
        _output({"action": "up"}, args.json)
