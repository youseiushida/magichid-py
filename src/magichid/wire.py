"""Protocol constants — the parts fixed by spec/protocol.yaml.
These are not design choices; they are the contract.
"""

from __future__ import annotations

PROTO_VERSION = 2
MAX_PAYLOAD = 192
HID_MAX_PAYLOAD = 63
DEDUP_WINDOW = 16
WATCHDOG_SECONDS = 0.5


class MsgType:
    SEND_REPORT = 0x01
    PING = 0x02
    RELEASE_ALL = 0x03
    GET_CAPS = 0x04
    SET_IDENTITY = 0x05
    SET_FEATURE = 0x06
    STATUS = 0x81
    ACK = 0x82
    NACK = 0x83
    HOST_EVENT = 0x84
    LOG = 0x85
    CAPS = 0x86


class StatusFlag:
    MOUNTED = 0x01
    SUSPENDED = 0x02
    READY = 0x04
    WATCHDOG = 0x08


class NackReason:
    BAD_CRC = 1
    BAD_LEN = 2
    UNKNOWN_ID = 3
    NOT_READY = 4
    NOT_SENDABLE = 5
    BAD_FRAME = 6
    TOO_BIG = 7

    _N = {1: "BAD_CRC", 2: "BAD_LEN", 3: "UNKNOWN_ID", 4: "NOT_READY",
          5: "NOT_SENDABLE", 6: "BAD_FRAME", 7: "TOO_BIG"}

    @classmethod
    def name(cls, code: int) -> str:
        return cls._N.get(code, f"UNKNOWN({code})")


class HidReportType:
    INPUT = 1; OUTPUT = 2; FEATURE = 3
    _N = {1: "INPUT", 2: "OUTPUT", 3: "FEATURE"}

    @classmethod
    def name(cls, code: int) -> str:
        return cls._N.get(code, f"UNKNOWN({code})")


class ReportFlag:
    RELATIVE = 0x01
