"""MagicHID CLI -- agent-native, non-interactive, structured by default.

Usage::

    magichid mouse move --x 10 --y -5 --json
    magichid keyboard tap --key ENTER
    magichid agent-context
"""

from __future__ import annotations

import argparse
import sys

from core.connection import Connection
from core.io.blocking import BlockingClient, BlockingError, CommandTimeout
from core.reports import ReportTable
from core.wire import MsgType, StatusFlag

from . import _mouse, _keyboard, _digitizer, _unicode, _soc, _horipad, _context
from ._common import output as _output, exit_fail as _exit

# ---------------------------------------------------------------------------
# Device registry
# ---------------------------------------------------------------------------

_DEVICE_MODULES = {
    "mouse": _mouse,
    "keyboard": _keyboard,
    "digitizer": _digitizer,
    "unicode": _unicode,
    "soc": _soc,
    "horipad": _horipad,
}


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def _connect(args: argparse.Namespace) -> BlockingClient:
    """Open serial, handshake, return :class:`BlockingClient`."""
    try:
        client = BlockingClient(port=args.port, baudrate=args.baudrate,
                                timeout=0.1)
    except Exception as exc:
        _exit(3, f"cannot open {args.port}: {exc}")

    try:
        status = client.handshake(timeout=args.handshake_timeout)
    except CommandTimeout:
        client.close()
        _exit(4, f"device at {args.port} not responding (mount and connect USB first)")
    except BlockingError as exc:
        client.close()
        _exit(4, str(exc))

    if not (status.flags & StatusFlag.MOUNTED) or not (status.flags & StatusFlag.READY):
        client.close()
        _exit(4, f"device not ready: flags=0x{status.flags:02X}")

    return client


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="magichid",
        description="MagicHID CLI -- USB-HID bridge controller",
    )
    p.add_argument("--port", default=None,
                   help="Serial port (e.g. COM3, /dev/ttyUSB0)")
    p.add_argument("--baudrate", type=int, default=1_000_000,
                   help="Serial baud rate (default: 1000000)")
    p.add_argument("--handshake-timeout", type=float, default=5.0,
                   help="Handshake timeout in seconds (default: 5)")
    p.add_argument("--json", action="store_true", default=False,
                   help="Emit JSON to stdout")

    sub = p.add_subparsers(dest="device", required=False,
                           help="Device type")

    for _name, _mod in _DEVICE_MODULES.items():
        _mod.register(sub)

    _context.register(sub)

    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.device is None:
        parser.print_help()
        _exit(1)

    # agent-context needs no device connection
    if args.device == "agent-context":
        _context.run(args)
        return

    # All other commands need --port
    if not args.port:
        _exit(2, "--port is required (e.g. --port COM3, --port /dev/ttyUSB0)")

    client = _connect(args)
    try:
        mod = _DEVICE_MODULES[args.device]
        mod.run(args, client)
    finally:
        try:
            client.send(MsgType.RELEASE_ALL, b"", reliable=False)
        except Exception:
            pass
        client.close()


if __name__ == "__main__":
    main()
