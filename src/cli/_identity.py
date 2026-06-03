"""USB identity/profile CLI subcommands."""

from __future__ import annotations

import argparse
import struct

from core.wire import MsgType

from ._common import output as _output, exit_fail as _exit

_PROFILES = {
    "universal": 0,
    "horipad": 1,
}


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("identity", help="Set USB identity/profile")
    sub2 = p.add_subparsers(dest="action", required=True)

    setp = sub2.add_parser("set", help="Persist USB identity/profile and reboot device")
    setp.add_argument("--profile", required=True, choices=sorted(_PROFILES),
                      help="USB profile to select")
    setp.add_argument("--vid", type=_u16, default=0,
                      help="USB VID. 0 keeps the profile default.")
    setp.add_argument("--pid", type=_u16, default=0,
                      help="USB PID. 0 keeps the profile default.")
    setp.add_argument("--bcd", type=_u16, default=0,
                      help="bcdDevice. 0 keeps the profile default.")


def run(args: argparse.Namespace, client) -> None:
    if args.action == "set":
        profile_id = _PROFILES[args.profile]
        payload = struct.pack("<HHHB", args.vid, args.pid, args.bcd, profile_id)
        client.request(MsgType.SET_IDENTITY, payload, reliable=True)
        _output({
            "action": "set",
            "profile": args.profile,
            "profile_id": profile_id,
            "vid": args.vid,
            "pid": args.pid,
            "bcd": args.bcd,
            "rebooting": True,
        }, args.json)


def _u16(value: str) -> int:
    try:
        parsed = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer, e.g. 0 or 0x0F0D") from exc
    if not 0 <= parsed <= 0xFFFF:
        raise argparse.ArgumentTypeError("must be between 0 and 0xFFFF")
    return parsed
