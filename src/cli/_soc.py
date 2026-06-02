"""SoC firmware update CLI subcommand."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.reports import ReportTable
from hid import SoCControl

from ._common import output as _output, exit_fail as _exit


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("soc", help="SoC firmware update (ESP32-S3)")
    sub2 = p.add_subparsers(dest="action", required=True)

    # firmware-chunk
    fc = sub2.add_parser("firmware-chunk", help="Send a 32-byte firmware chunk")
    fc.add_argument("--firmware-id", type=int, required=True,
                    help="File identifier (0-65535)")
    fc.add_argument("--offset", type=int, required=True,
                    help="Byte offset in the firmware file (0-2^31-1)")
    fc.add_argument("--payload-file", type=Path, required=True,
                    help="Path to a file containing the chunk payload (max 32 bytes)")
    fc.add_argument("--is-last", action="store_true", default=False,
                    help="Mark this as the final chunk")


def run(args: argparse.Namespace, client) -> None:
    table = ReportTable.universal()
    soc = SoCControl(client, table)

    if args.action == "firmware-chunk":
        try:
            payload = args.payload_file.read_bytes()
        except OSError as exc:
            _exit(5, f"cannot read {args.payload_file}: {exc}")
        if len(payload) > 32:
            _exit(5, f"payload file {args.payload_file} is {len(payload)} bytes; "
                     f"max is 32 bytes")
        soc.set_firmware_chunk(
            firmware_id=args.firmware_id,
            offset=args.offset,
            payload=payload,
            is_last=args.is_last,
        )
        _output({
            "action": "firmware-chunk",
            "firmware_id": args.firmware_id,
            "offset": args.offset,
            "size": len(payload),
            "is_last": args.is_last,
        }, args.json)
