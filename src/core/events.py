"""Events emitted by the sans-I/O :class:`Connection`.

Every observable occurrence — including corrupt frames and version mismatches —
is an event. The edge decides what to escalate; the core never swallows silently.
"""

from __future__ import annotations

from dataclasses import dataclass

from .wire import HidReportType, NackReason, ReportFlag, StatusFlag


class Event:
    """Marker base."""


@dataclass(frozen=True)
class StatusReceived(Event):
    flags: int
    proto_version: int

    @property
    def mounted(self) -> bool: return bool(self.flags & StatusFlag.MOUNTED)

    @property
    def suspended(self) -> bool: return bool(self.flags & StatusFlag.SUSPENDED)

    @property
    def ready(self) -> bool: return bool(self.flags & StatusFlag.READY)

    @property
    def watchdog(self) -> bool: return bool(self.flags & StatusFlag.WATCHDOG)


@dataclass(frozen=True)
class SessionOpened(Event):
    """Reply to SESSION_OPEN: the device-minted epoch for this operator session.

    The device cleared its SEQ dedup window when it minted this epoch, so the
    client may safely restart its SEQ counter at 1 for the new session.
    """
    epoch: int


@dataclass(frozen=True)
class Acknowledged(Event):
    seq: int


@dataclass(frozen=True)
class Rejected(Event):
    seq: int
    reason: int

    @property
    def reason_name(self) -> str: return NackReason.name(self.reason)


@dataclass(frozen=True)
class HostEventReceived(Event):
    report_id: int
    report_type: int
    data: bytes

    @property
    def type_name(self) -> str: return HidReportType.name(self.report_type)


@dataclass(frozen=True)
class LogReceived(Event):
    text: str


@dataclass(frozen=True)
class ReportCap:
    """One row of a CAPS table (a value, not an event by itself)."""
    id: int
    in_len: int
    out_len: int
    feat_len: int
    flags: int

    @property
    def relative(self) -> bool: return bool(self.flags & ReportFlag.RELATIVE)

    @property
    def sendable(self) -> bool: return self.in_len > 0


@dataclass(frozen=True)
class CapsReceived(Event):
    """A CAPS reply matched to its request SEQ."""
    seq: int
    entries: tuple[ReportCap, ...]


@dataclass(frozen=True)
class VersionMismatch(Event):
    got: int
    expected: int


@dataclass(frozen=True)
class FrameError(Event):
    detail: str


@dataclass(frozen=True)
class NackUnmatched(Event):
    """NACK with seq=0 (e.g. BAD_CRC) — diagnostic only, no command to match."""
    reason: int

    @property
    def reason_name(self) -> str: return NackReason.name(self.reason)


@dataclass(frozen=True)
class UnknownFrame(Event):
    type: int
    seq: int
    payload: bytes
