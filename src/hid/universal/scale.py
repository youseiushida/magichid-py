"""Scales device (report ID 30, 6-byte INPUT + 1-byte OUTPUT).

Conforms to:
* universal_reports.yaml — report ID 30, Page 0x008D (Scales), Scales

INPUT:  ``[weight:4][scaling:1][status:1]`` (u32 LE + s8 + u8)
OUTPUT: ``[zero_scale:1+pad:7]`` — host requests tare/zero
"""

from __future__ import annotations

import struct

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 30

_F_ZERO = 1 << 0


class Scale:
    """Weighing scale — weight + scaling + status, zero command from host.

    Usage::

        scale = Scale(client, ReportTable.universal())

        scale.set(weight=150000, scaling=-2, status=0)

        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                scale.handle_host_event(ev)
        if scale.zero_requested:
            ...
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._weight: int = 0
        self._scaling: int = 0
        self._status: int = 0
        self._zero_requested: bool = False

    # -- INPUT state ---------------------------------------------------------- #

    @property
    def weight(self) -> int:
        """Measured weight (raw, 0–2³¹-1)."""
        return self._weight

    @property
    def scaling(self) -> int:
        """Scaling exponent (-128..127)."""
        return self._scaling

    @property
    def status(self) -> int:
        """Scale status byte (0–255)."""
        return self._status

    def set(
        self,
        *,
        weight: int | None = None,
        scaling: int | None = None,
        status: int | None = None,
    ) -> None:
        """Set weight, scaling, and/or status, then send a report."""
        if weight is not None:
            self._weight = _clamp_u32(weight)
        if scaling is not None:
            self._scaling = _clamp_s8(scaling)
        if status is not None:
            self._status = _clamp_u8(status)
        self._send_input()

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def zero_requested(self) -> bool:
        """True if the host sent a zero/tare command."""
        return self._zero_requested

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            self._zero_requested = bool(event.data[0] & _F_ZERO)

    # -- internals ------------------------------------------------------------ #

    def _send_input(self) -> None:
        report = struct.pack(
            "<IbB", self._weight & 0xFFFFFFFF, self._scaling, self._status & 0xFF,
        )
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _clamp_u32(v: int) -> int:
    return max(0, min(2147483647, v))


def _clamp_s8(v: int) -> int:
    return max(-128, min(127, v))


def _clamp_u8(v: int) -> int:
    return max(0, min(255, v))
